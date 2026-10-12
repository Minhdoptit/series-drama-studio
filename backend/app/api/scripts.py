import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_session
from app.models import Project, Episode, Script, Scene, User, ApiKey, Image
from app.services.auth_service import get_current_user
from app.services.cascade_service import delete_scenes_of_script
from app.services.llm_service import generate_script_from_prompt, parse_scenes_from_content

router = APIRouter()


class Character(BaseModel):
    name: str
    age: Optional[str] = None
    description: Optional[str] = None


class GenerateScriptRequest(BaseModel):
    title: Optional[str] = None
    style: Optional[str] = None
    characters: List[Character] = []
    content: str
    duration_sec: int = 50
    document_ids: List[str] = []


class ImageInfo(BaseModel):
    id: str
    label: Optional[str] = None
    file_path: str
    type: Optional[str] = None


class SceneOut(BaseModel):
    id: str
    scene_no: int
    location: Optional[str]
    action_desc: Optional[str]
    shot_type: Optional[str]
    duration_sec: Optional[float]
    voice_over: Optional[str]
    image_id: Optional[str]
    image_ids: List[str] = []
    images: List[ImageInfo] = []
    extra_prompt: Optional[str] = None


class ScriptOut(BaseModel):
    id: str
    episode_id: str
    title: Optional[str]
    content: str
    created_at: datetime
    version: int = 1
    is_active: bool = True
    scenes: List[SceneOut] = []


# Các trường cảnh cho phép sửa qua PATCH. Trước đây dùng hasattr() nên client
# có thể ghi đè cả `id` và `script_id`, tức là chuyển cảnh sang kịch bản khác.
_SCENE_EDITABLE_FIELDS = {
    "scene_no", "location", "action_desc", "shot_type",
    "duration_sec", "voice_over", "extra_prompt", "image_id",
}


# ─── Helpers ─────────────────────────────────────────────

async def _get_project(project_id: str, user: User, session: AsyncSession) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Không tìm thấy dự án")
    return p


async def _get_episode(episode_id: str, project_id: str, session: AsyncSession) -> Episode:
    result = await session.execute(
        select(Episode).where(Episode.id == episode_id, Episode.project_id == project_id)
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(404, "Không tìm thấy tập")
    return ep


async def _load_scenes(script_id: str, session: AsyncSession) -> List[SceneOut]:
    scenes_res = await session.execute(
        select(Scene).where(Scene.script_id == script_id).order_by(Scene.scene_no)
    )
    scenes = scenes_res.scalars().all()

    all_image_ids = set()
    scene_img_map = {}
    for s in scenes:
        ids = []
        if s.image_ids:
            try:
                ids = json.loads(s.image_ids)
            except Exception:
                ids = []
        elif s.image_id:
            ids = [s.image_id]
        scene_img_map[s.id] = ids
        all_image_ids.update(ids)

    image_dict = {}
    if all_image_ids:
        img_res = await session.execute(select(Image).where(Image.id.in_(list(all_image_ids))))
        for img in img_res.scalars().all():
            # Thêm /data/ prefix để frontend build đúng URL (/data/assets/...)
            fp = img.file_path
            if fp and not fp.startswith("/data/"):
                fp = f"/data/{fp}"
            image_dict[img.id] = ImageInfo(
                id=img.id,
                label=img.label,
                file_path=fp,
                type=img.type.value if hasattr(img.type, 'value') else str(img.type)
            )

    result_scenes = []
    for s in scenes:
        img_ids = scene_img_map.get(s.id, [])
        img_objs = [image_dict[iid] for iid in img_ids if iid in image_dict]
        s_out = SceneOut(
            id=s.id,
            scene_no=s.scene_no,
            location=s.location,
            action_desc=s.action_desc,
            shot_type=s.shot_type,
            duration_sec=s.duration_sec,
            voice_over=s.voice_over,
            image_id=s.image_id,
            image_ids=img_ids,
            images=img_objs,
            extra_prompt=s.extra_prompt,
        )
        result_scenes.append(s_out)

    return result_scenes


# ─── Generate kịch bản ────────────────────────────────────

@router.post("/{project_id}/episodes/{episode_id}/scripts/generate")
async def generate_script(
    project_id: str,
    episode_id: str,
    body: GenerateScriptRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project(project_id, current_user, session)
    await _get_episode(episode_id, project_id, session)

    result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    api_key_config = result.scalar_one_or_none()
    if not api_key_config or not api_key_config.llm_key_enc:
        raise HTTPException(400, "Chưa cấu hình API key cho LLM. Vào Cài đặt để thêm key.")

    doc_texts = []
    if body.document_ids:
        from app.models import Document
        for doc_id in body.document_ids:
            res = await session.execute(
                select(Document).where(Document.id == doc_id, Document.project_id == project_id)
            )
            doc = res.scalar_one_or_none()
            if doc and doc.extracted_text:
                doc_texts.append(f"=== {doc.file_name} ===\n{doc.extracted_text}")

    try:
        result_data = await generate_script_from_prompt(
            title=body.title,
            style=body.style,
            characters=body.characters,
            content=body.content,
            duration_sec=body.duration_sec,
            doc_texts=doc_texts,
            api_config=api_key_config,
        )
    except Exception as e:
        import traceback, logging
        logger = logging.getLogger("scripts")
        logger.error(
            f"[GenScript] provider={api_key_config.llm_provider} "
            f"model={api_key_config.llm_model} error={e}\n"
            + traceback.format_exc()
        )
        raise HTTPException(500, f"Lỗi gen kịch bản: {str(e)}")
    return result_data


# ─── Lưu kịch bản (tạo phiên bản mới) ───────────────────

@router.post("/{project_id}/episodes/{episode_id}/scripts/save", response_model=ScriptOut, status_code=201)
async def save_script(
    project_id: str,
    episode_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project(project_id, current_user, session)
    await _get_episode(episode_id, project_id, session)

    # Lấy id script đang active (để set parent_id)
    result_active = await session.execute(
        select(Script.id).where(
            Script.episode_id == episode_id,
            Script.is_active == True,
        )
    )
    active_id = result_active.scalar_one_or_none()

    # Tính version mới
    result_max = await session.execute(
        select(func.max(Script.version)).where(Script.episode_id == episode_id)
    )
    max_version = result_max.scalar() or 0

    # Deactivate tất cả scripts cũ của episode
    await session.execute(
        update(Script)
        .where(Script.episode_id == episode_id)
        .values(is_active=False)
    )

    # Insert script mới
    script = Script(
        project_id=project_id,
        episode_id=episode_id,
        title=body.get("title"),
        content=body.get("content", ""),
        prompt_used=body.get("prompt_used"),
        version=max_version + 1,
        is_active=True,
        parent_id=active_id,
    )
    session.add(script)
    await session.flush()

    # Insert scenes nếu có (chỉ khi gen mới, không phải khi edit)
    scenes = []
    for s in body.get("scenes", []):
        scene = Scene(
            script_id=script.id,
            scene_no=s.get("scene_no", 0),
            location=s.get("location"),
            action_desc=s.get("action_desc"),
            shot_type=s.get("shot_type"),
            duration_sec=s.get("duration_sec"),
            voice_over=s.get("voice_over"),
        )
        session.add(scene)
        scenes.append(scene)

    await session.commit()
    await session.refresh(script)
    return ScriptOut(
        id=script.id,
        episode_id=script.episode_id,
        title=script.title,
        content=script.content,
        created_at=script.created_at,
        version=script.version,
        is_active=script.is_active,
        # Cảnh vừa tạo chưa gán ảnh nào nên image_ids/images luôn rỗng.
        # Không dùng getattr theo model_fields: Scene không có thuộc tính `images`,
        # còn `image_ids` là chuỗi JSON chứ không phải List[str].
        scenes=[
            SceneOut(
                id=sc.id,
                scene_no=sc.scene_no,
                location=sc.location,
                action_desc=sc.action_desc,
                shot_type=sc.shot_type,
                duration_sec=sc.duration_sec,
                voice_over=sc.voice_over,
                image_id=None,
                image_ids=[],
                images=[],
                extra_prompt=sc.extra_prompt,
            )
            for sc in scenes
        ],
    )


# ─── Danh sách kịch bản theo tập ─────────────────────────

@router.get("/{project_id}/episodes/{episode_id}/scripts", response_model=List[ScriptOut])
async def list_scripts(
    project_id: str,
    episode_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project(project_id, current_user, session)
    await _get_episode(episode_id, project_id, session)

    result = await session.execute(
        select(Script).where(Script.episode_id == episode_id).order_by(Script.version.desc())
    )
    scripts = result.scalars().all()
    out = []
    for sc in scripts:
        out.append(ScriptOut(
            id=sc.id,
            episode_id=sc.episode_id,
            title=sc.title,
            content=sc.content,
            created_at=sc.created_at,
            version=sc.version,
            is_active=sc.is_active,
            scenes=await _load_scenes(sc.id, session),
        ))
    return out


# ─── Cập nhật scene ──────────────────────────────────────

@router.patch("/{project_id}/scenes/{scene_id}")
async def update_scene(
    project_id: str,
    scene_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project(project_id, current_user, session)
    # Cảnh phải nằm trong project này (join Script→Episode), nếu không user
    # có thể sửa cảnh của người khác chỉ bằng cách đoán scene_id.
    result = await session.execute(
        select(Scene)
        .join(Script, Script.id == Scene.script_id)
        .join(Episode, Episode.id == Script.episode_id)
        .where(Scene.id == scene_id, Episode.project_id == project_id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(404, "Không tìm thấy cảnh")
    for k, v in body.items():
        if k == "image_ids":
            if isinstance(v, list):
                scene.image_ids = json.dumps(v)
                scene.image_id = v[0] if v else None
            elif isinstance(v, str):
                scene.image_ids = v
        elif k in _SCENE_EDITABLE_FIELDS:
            setattr(scene, k, v)
    session.add(scene)
    await session.commit()
    await session.refresh(scene)
    return scene


# ─── Rollback: activate phiên bản cũ ─────────────────────

@router.patch("/{project_id}/episodes/{episode_id}/scripts/{script_id}/activate")
async def activate_script(
    project_id: str,
    episode_id: str,
    script_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Rollback: đặt script_id thành active, deactivate tất cả bản còn lại."""
    await _get_project(project_id, current_user, session)
    await _get_episode(episode_id, project_id, session)

    result = await session.execute(
        select(Script).where(Script.id == script_id, Script.episode_id == episode_id)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Không tìm thấy phiên bản kịch bản")

    # Deactivate tất cả, activate script được chọn
    await session.execute(
        update(Script).where(Script.episode_id == episode_id).values(is_active=False)
    )
    script.is_active = True
    session.add(script)
    await session.commit()
    return {"message": f"Đã khôi phục phiên bản v{script.version}"}


# ─── Reparse scenes (preview) ────────────────────────────

@router.post("/{project_id}/episodes/{episode_id}/scripts/{script_id}/reparse-scenes")
async def reparse_scenes(
    project_id: str,
    episode_id: str,
    script_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Parse lại scenes từ content hiện tại của script — chỉ preview, chưa lưu."""
    await _get_project(project_id, current_user, session)
    # episode_id đến từ URL: phải xác nhận tập thuộc project này trước khi
    # cho đọc/ghi kịch bản của nó.
    await _get_episode(episode_id, project_id, session)

    result = await session.execute(
        select(Script).where(Script.id == script_id, Script.episode_id == episode_id)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Không tìm thấy kịch bản")

    api_key_result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    api_config = api_key_result.scalar_one_or_none()
    if not api_config or not api_config.llm_key_enc:
        raise HTTPException(400, "Chưa cấu hình API key LLM. Vào Cài đặt để thêm key.")

    try:
        scenes = await parse_scenes_from_content(script.content, api_config)
    except Exception as e:
        raise HTTPException(500, f"Lỗi parse cảnh: {str(e)}")

    return {"scenes": scenes, "count": len(scenes)}


# ─── Confirm reparse (apply) ─────────────────────────────

@router.post("/{project_id}/episodes/{episode_id}/scripts/{script_id}/reparse-scenes/confirm")
async def confirm_reparse(
    project_id: str,
    episode_id: str,
    script_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Xóa scenes cũ, insert scenes mới từ body.scenes."""
    await _get_project(project_id, current_user, session)
    # episode_id đến từ URL: phải xác nhận tập thuộc project này trước khi
    # cho đọc/ghi kịch bản của nó.
    await _get_episode(episode_id, project_id, session)

    result = await session.execute(
        select(Script).where(Script.id == script_id, Script.episode_id == episode_id)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Không tìm thấy kịch bản")

    # Xóa scenes cũ — phải xoá Video con trước, nếu không sẽ vi phạm khoá ngoại
    # videos.scene_id với những cảnh đã gen video.
    await delete_scenes_of_script(session, script_id)

    # Insert scenes mới
    new_scenes = []
    for s in body.get("scenes", []):
        scene = Scene(
            script_id=script_id,
            scene_no=s.get("scene_no", 0),
            location=s.get("location"),
            action_desc=s.get("action_desc"),
            shot_type=s.get("shot_type"),
            duration_sec=s.get("duration_sec"),
            voice_over=s.get("voice_over"),
        )
        session.add(scene)
        new_scenes.append(scene)

    await session.commit()
    return {"message": f"Đã cập nhật {len(new_scenes)} cảnh"}
