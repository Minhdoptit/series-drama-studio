from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional, List
import pathlib, os, httpx, base64, aiofiles, uuid

from app.database import get_session
from app.models import Image, Project, User, ImageType, ApiKey, Episode
from app.services.auth_service import get_current_user
from app.services.image_service import generate_images_ai

router = APIRouter()
DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))


class GenerateImageRequest(BaseModel):
    type: ImageType = ImageType.character
    label: Optional[str] = None
    prompt: str
    style: Optional[str] = "3D Pixar mềm, nhân vật con vật cách điệu dáng người"
    reference_image_ids: List[str] = []
    episode_id: Optional[str] = None   # None = ảnh chung project (nhân vật)


async def _check_project(project_id: str, user: User, session: AsyncSession):
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Không tìm thấy dự án")


# ─── Generate ảnh ─────────────────────────────────────────

@router.post("/{project_id}/images/generate")
async def generate_images(
    project_id: str,
    body: GenerateImageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _check_project(project_id, current_user, session)

    result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    api_key_config = result.scalar_one_or_none()
    if not api_key_config or not api_key_config.image_key_enc:
        raise HTTPException(400, "Chưa cấu hình API key cho Image Generation. Vào Cài đặt để thêm.")

    # Load ảnh tham chiếu
    ref_images_b64 = []
    for img_id in body.reference_image_ids:
        res = await session.execute(
            select(Image).where(Image.id == img_id, Image.project_id == project_id)
        )
        img = res.scalar_one_or_none()
        if img:
            full_path = DATA_DIR / img.file_path
            if full_path.exists():
                async with aiofiles.open(full_path, "rb") as f:
                    data = await f.read()
                ref_images_b64.append(base64.b64encode(data).decode())

    try:
        image_urls = await generate_images_ai(
            prompt=body.prompt,
            style=body.style,
            reference_images_b64=ref_images_b64,
            api_config=api_key_config,
            n=3,
        )
    except Exception as e:
        # Không để lỗi rơi ra thành 500 "Internal Server Error" — user cần thấy
        # lý do thật (hết quota, key sai, model không hỗ trợ...)
        import logging, traceback
        logging.getLogger("images").error(
            f"[GenImage] provider={api_key_config.image_provider} "
            f"model={api_key_config.image_model} error={e}\n" + traceback.format_exc()
        )
        raise HTTPException(500, f"Lỗi gen ảnh: {e}")

    return {"images": image_urls, "prompt": body.prompt}


# ─── Lưu ảnh ─────────────────────────────────────────────

@router.post("/{project_id}/images/save", status_code=201)
async def save_image(
    project_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Lưu ảnh được gen (từ URL hoặc base64) vào thư viện.
    episode_id = null → ảnh nhân vật chung
    episode_id = <id> → ảnh riêng tập (bối cảnh, đạo cụ)
    """
    await _check_project(project_id, current_user, session)

    # episode_id đến từ body: phải xác nhận tập đó thuộc project này,
    # nếu không user có thể gán ảnh vào tập của người khác.
    episode_id = body.get("episode_id")
    if episode_id:
        ep_res = await session.execute(
            select(Episode.id).where(Episode.id == episode_id, Episode.project_id == project_id)
        )
        if ep_res.scalar_one_or_none() is None:
            raise HTTPException(404, "Không tìm thấy tập trong dự án này")

    asset_dir = DATA_DIR / "assets" / project_id
    asset_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())[:8]
    file_path = asset_dir / f"img_{file_id}.png"

    image_src = body.get("image_url") or body.get("image_b64")
    if not image_src:
        raise HTTPException(400, "Cần image_url hoặc image_b64")

    if body.get("image_url"):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(image_src)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(resp.content)
    else:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(base64.b64decode(image_src))

    rel_path = str(file_path.relative_to(DATA_DIR))

    image = Image(
        project_id=project_id,
        episode_id=episode_id,   # None = ảnh chung
        type=ImageType(body.get("type", "character")),
        label=body.get("label"),
        prompt=body.get("prompt"),
        style=body.get("style"),
        file_path=rel_path,
        thumbnail_path=rel_path,
        provider=body.get("provider"),
        model=body.get("model"),
    )
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return {"id": image.id, "file_path": f"/data/{rel_path}"}


# ─── Danh sách ảnh ───────────────────────────────────────

@router.get("/{project_id}/images")
async def list_images(
    project_id: str,
    type: Optional[str] = None,
    episode_id: Optional[str] = None,
    shared: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Query params:
      shared=true         → ảnh nhân vật chung (episode_id IS NULL)
      episode_id=<id>     → ảnh riêng tập
      (không có gì)       → tất cả ảnh trong project
    """
    await _check_project(project_id, current_user, session)
    q = select(Image).where(Image.project_id == project_id)

    if shared:
        q = q.where(Image.episode_id.is_(None))
    elif episode_id:
        q = q.where(Image.episode_id == episode_id)

    if type:
        q = q.where(Image.type == type)

    result = await session.execute(q.order_by(Image.created_at.desc()))
    images = result.scalars().all()
    return [
        {
            "id": img.id,
            "type": img.type,
            "label": img.label,
            "prompt": img.prompt,
            "style": img.style,
            "episode_id": img.episode_id,
            "url": f"/data/{img.file_path}",
            "created_at": img.created_at,
        }
        for img in images
    ]


# ─── Đổi tên ảnh ─────────────────────────────────────────

@router.patch("/{project_id}/images/{image_id}")
async def update_image(
    project_id: str,
    image_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cập nhật thông tin ảnh (label)."""
    await _check_project(project_id, current_user, session)
    result = await session.execute(
        select(Image).where(Image.id == image_id, Image.project_id == project_id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(404, "Không tìm thấy ảnh")
    if "label" in body:
        img.label = body["label"]
    session.add(img)
    await session.commit()
    return {"id": img.id, "label": img.label}


# ─── Xoá ảnh ─────────────────────────────────────────────

@router.delete("/{project_id}/images/{image_id}", status_code=204)
async def delete_image(
    project_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _check_project(project_id, current_user, session)
    result = await session.execute(
        select(Image).where(Image.id == image_id, Image.project_id == project_id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(404, "Không tìm thấy ảnh")
    try:
        p = DATA_DIR / img.file_path
        if p.exists():
            p.unlink()
    except Exception:
        pass
    await session.delete(img)
    await session.commit()

