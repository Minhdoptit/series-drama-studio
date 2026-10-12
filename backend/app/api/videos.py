from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os, pathlib, uuid

from app.database import get_session, AsyncSessionLocal
from app.models import Video, Scene, Script, Project, User, VideoStatus, ApiKey, Image, Episode, utcnow
from app.services.auth_service import get_current_user
from app.services.video_service import generate_video_ai, concat_videos

router = APIRouter()
DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))


# ─── Kiểm tra quyền sở hữu ────────────────────────────────
# Mọi endpoint nhận id trong URL đều phải xác nhận bản ghi thuộc về project của
# user đang đăng nhập; nếu không, ai biết id là truy cập được dữ liệu người khác.

async def _assert_project_owned(project_id: str, user: User, session: AsyncSession) -> None:
    res = await session.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(404, "Không tìm thấy project")


async def _get_owned_video(video_id: str, project_id: str, user: User, session: AsyncSession) -> Video:
    """Lấy Video và xác nhận nó nằm trong project của user (join Scene→Script→Episode)."""
    res = await session.execute(
        select(Video)
        .join(Scene, Scene.id == Video.scene_id)
        .join(Script, Script.id == Scene.script_id)
        .join(Episode, Episode.id == Script.episode_id)
        .join(Project, Project.id == Episode.project_id)
        .where(
            Video.id == video_id,
            Episode.project_id == project_id,
            Project.user_id == user.id,
        )
    )
    video = res.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Không tìm thấy video")
    return video


async def _get_owned_episode(episode_id: str, project_id: str, user: User, session: AsyncSession) -> Episode:
    res = await session.execute(
        select(Episode)
        .join(Project, Project.id == Episode.project_id)
        .where(
            Episode.id == episode_id,
            Episode.project_id == project_id,
            Project.user_id == user.id,
        )
    )
    ep = res.scalar_one_or_none()
    if not ep:
        raise HTTPException(404, "Không tìm thấy tập")
    return ep


class GenerateVideoRequest(BaseModel):
    scene_ids: List[str]
    video_size: str = "720x1280"  # default 9:16 portrait
    duration: int = 5            # 5 hoặc 10 giây (Z.AI hỗ trợ 5s và 10s)

# Mapping ti le -> Z.AI size enum
_VALID_SIZES = {
    "720x1280", "1280x720", "1024x1024",
    "1080x1920", "2048x1080", "3840x2160",
}

async def _run_video_generation(video_id: str, scene_id: str, extra_prompt: Optional[str], video_size: str = "720x1280", duration: int = 5):
    """Background task: generate video for one scene."""
    async with AsyncSessionLocal() as session:
        # Get video record
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if not video:
            return

        # Get scene + image + api config
        result = await session.execute(select(Scene).where(Scene.id == scene_id))
        scene = result.scalar_one_or_none()
        if not scene:
            video.status = VideoStatus.error
            video.error_msg = "Không tìm thấy cảnh"
            session.add(video)
            await session.commit()
            return

        # Get script → project → user
        result = await session.execute(select(Script).where(Script.id == scene.script_id))
        script = result.scalar_one_or_none()
        result2 = await session.execute(select(Project).where(Project.id == script.project_id))
        project = result2.scalar_one_or_none()

        result3 = await session.execute(select(ApiKey).where(ApiKey.user_id == project.user_id))
        api_config = result3.scalar_one_or_none()

        if not api_config or not api_config.video_key_enc:
            video.status = VideoStatus.error
            video.error_msg = "Chưa cấu hình API key cho Video Generation"
            session.add(video)
            await session.commit()
            return

        # Get reference images
        import json
        images_data = []
        target_img_ids = []
        if scene.image_ids:
            try:
                target_img_ids = json.loads(scene.image_ids)
            except Exception:
                target_img_ids = []
        if not target_img_ids and scene.image_id:
            target_img_ids = [scene.image_id]

        if target_img_ids:
            res = await session.execute(select(Image).where(Image.id.in_(target_img_ids)))
            imgs = res.scalars().all()
            img_map = {img.id: img for img in imgs}
            import os, pathlib
            DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))
            for iid in target_img_ids:
                if iid in img_map:
                    img = img_map[iid]
                    p = str(DATA_DIR / img.file_path)
                    if pathlib.Path(p).exists():
                        images_data.append({"path": p, "label": img.label or "Nhân vật/Bối cảnh"})

        try:
            video.status = VideoStatus.running
            video.started_at = utcnow()
            session.add(video)
            await session.commit()

            file_path = await generate_video_ai(
                scene=scene,
                images_data=images_data,
                extra_prompt=extra_prompt,
                api_config=api_config,
                project_id=script.project_id,
                video_size=video_size,
                duration=duration,
            )

            video.status = VideoStatus.done
            video.file_path = file_path
            video.completed_at = utcnow()
        except Exception as e:
            video.status = VideoStatus.error
            video.error_msg = str(e)[:500]

        session.add(video)
        await session.commit()


async def cleanup_old_scene_videos(session: AsyncSession, scene_id: str, max_keep: int = 2):
    """
    Chỉ giữ tối đa `max_keep` (2) video mới nhất cho scene_id, xoá bớt bản ghi cũ
    trong DB và file trên đĩa.

    KHÔNG đụng vào video đang pending/running: task nền giữ bản ghi đó trong
    session riêng và sẽ commit lúc gen xong — nếu hàng bị xoá mất, lệnh UPDATE
    khớp 0 dòng và SQLAlchemy ném StaleDataError.
    """
    res = await session.execute(
        select(Video).where(Video.scene_id == scene_id).order_by(Video.created_at.desc())
    )
    vids = res.scalars().all()
    deletable = [
        v for v in vids
        if v.status not in (VideoStatus.pending, VideoStatus.running)
    ]
    # Giữ lại `max_keep` video mới nhất tính trên toàn bộ danh sách
    keep_ids = {v.id for v in vids[:max_keep]}
    for old_v in deletable:
        if old_v.id in keep_ids:
            continue
        if old_v.file_path:
            p = DATA_DIR / old_v.file_path
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        await session.delete(old_v)


async def cleanup_all_old_videos():
    """Dọn dẹp toàn bộ DB: mỗi scene chỉ giữ tối đa 2 video mới nhất."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Video.scene_id).distinct())
        scene_ids = [row[0] for row in res.fetchall() if row[0]]
        for sid in scene_ids:
            await cleanup_old_scene_videos(session, sid, max_keep=2)
        await session.commit()


@router.post("/{project_id}/videos/generate", status_code=202)
async def generate_videos(
    project_id: str,
    body: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _assert_project_owned(project_id, current_user, session)

    video_ids = []
    for scene_id in body.scene_ids:
        # Chỉ nhận cảnh thuộc project này — tránh gen video lên cảnh của người khác
        res = await session.execute(
            select(Scene)
            .join(Script, Script.id == Scene.script_id)
            .join(Episode, Episode.id == Script.episode_id)
            .where(Scene.id == scene_id, Episode.project_id == project_id)
        )
        scene = res.scalar_one_or_none()
        if not scene:
            continue

        video = Video(scene_id=scene_id, status=VideoStatus.pending)
        session.add(video)
        await session.flush()

        # Dọn dẹp: chỉ giữ video mới này + 1 video ngay trước đó (tối đa 2 video trong DB cho scene này)
        await cleanup_old_scene_videos(session, scene_id, max_keep=2)

        video_ids.append(video.id)
        # Validate size & duration
        size = body.video_size if body.video_size in _VALID_SIZES else "720x1280"
        dur = 10 if body.duration == 10 else 5
        background_tasks.add_task(
            _run_video_generation, video.id, scene_id, scene.extra_prompt, size, dur
        )

    await session.commit()
    return {"message": f"Đang gen {len(video_ids)} video", "video_ids": video_ids}


@router.get("/{project_id}/videos")
async def list_videos(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _assert_project_owned(project_id, current_user, session)

    result = await session.execute(
        select(Video)
        .join(Scene, Scene.id == Video.scene_id)
        .join(Script, Script.id == Scene.script_id)
        .join(Episode, Episode.id == Script.episode_id)
        .where(Episode.project_id == project_id)
        .order_by(Video.created_at.desc())
    )
    videos = result.scalars().all()

    # Chi giu video MOI NHAT moi scene (ORDER BY DESC nen phan tu dau la moi nhat)
    seen: dict = {}
    for v in videos:
        if v.scene_id not in seen:
            seen[v.scene_id] = v

    return [
        {
            "id": v.id, "scene_id": v.scene_id, "status": v.status,
            "file_path": f"/data/{v.file_path}" if v.file_path else None,
            "error_msg": v.error_msg,
            "created_at": v.created_at,
            "started_at": v.started_at,
            "completed_at": v.completed_at,
        }
        for v in seen.values()
    ]


@router.get("/{project_id}/videos/{video_id}")
async def get_video_status(
    project_id: str,
    video_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    video = await _get_owned_video(video_id, project_id, current_user, session)
    return {
        "id": video.id, "scene_id": video.scene_id, "status": video.status,
        "file_path": f"/data/{video.file_path}" if video.file_path else None,
        "error_msg": video.error_msg,
        "started_at": video.started_at,
        "completed_at": video.completed_at,
    }


@router.delete("/{project_id}/videos/{video_id}", status_code=204)
async def delete_video(
    project_id: str,
    video_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    video = await _get_owned_video(video_id, project_id, current_user, session)
    if video.file_path:
        p = DATA_DIR / video.file_path
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    await session.delete(video)
    await session.commit()


# ─── Tải video ─────────────────────────────────────

@router.get("/{project_id}/videos/{video_id}/download")
async def download_video(
    project_id: str,
    video_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Tải video lẻ của một cảnh."""
    video = await _get_owned_video(video_id, project_id, current_user, session)
    if video.status != VideoStatus.done or not video.file_path:
        raise HTTPException(404, "Video chưa sẵn sàng")
    path = DATA_DIR / video.file_path
    if not path.exists():
        raise HTTPException(404, "File video không tồn tại")
    return FileResponse(
        path=str(path),
        media_type="video/mp4",
        filename=path.name,
    )


# ─── Ghép tập (merge all scenes) ──────────────────────

async def _run_merge(episode_id: str, project_id: str):
    """Background task: ghép tất cả video của episode thành 1 file."""
    async with AsyncSessionLocal() as session:
        # Lấy episode
        ep_res = await session.execute(select(Episode).where(Episode.id == episode_id))
        episode = ep_res.scalar_one_or_none()
        if not episode:
            return

        try:
            # Cập nhật trạng thái
            episode.merged_video_status = "merging"
            session.add(episode)
            await session.commit()

            # Lấy scenes của kịch bản đang active trong tập, sắp xếp theo số cảnh.
            # Scene gắn với Script (không gắn trực tiếp episode) nên phải join qua Script.
            scenes_res = await session.execute(
                select(Scene)
                .join(Script, Script.id == Scene.script_id)
                .where(Script.episode_id == episode_id, Script.is_active == True)
                .order_by(Scene.scene_no)
            )
            scenes = scenes_res.scalars().all()

            # Lấy video done mới nhất cho mỗi scene
            clip_paths = []
            for scene in scenes:
                vid_res = await session.execute(
                    select(Video)
                    .where(Video.scene_id == scene.id, Video.status == VideoStatus.done)
                    .order_by(Video.completed_at.desc())
                )
                vid = vid_res.scalars().first()
                if vid and vid.file_path:
                    p = DATA_DIR / vid.file_path
                    if p.exists():
                        clip_paths.append(str(p))

            if not clip_paths:
                episode.merged_video_status = "error"
                episode.merged_video_error = "Không có video nào để ghép"
                session.add(episode)
                await session.commit()
                return

            # Đường dẫn output
            out_dir = DATA_DIR / "videos" / project_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"episode_{episode_id[:8]}_{uuid.uuid4().hex[:6]}.mp4"
            out_path = out_dir / out_name

            await concat_videos(clip_paths, str(out_path))

            rel_path = str(out_path.relative_to(DATA_DIR))
            episode.merged_video_path = rel_path
            episode.merged_video_status = "done"
            episode.merged_video_error = None

        except Exception as e:
            episode.merged_video_status = "error"
            episode.merged_video_error = str(e)[:500]

        session.add(episode)
        await session.commit()


@router.post("/{project_id}/episodes/{episode_id}/videos/merge", status_code=202)
async def merge_episode_videos(
    project_id: str,
    episode_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Ghép tất cả video của các cảnh trong tập thành 1 file hoàn chỉnh."""
    await _get_owned_episode(episode_id, project_id, current_user, session)

    background_tasks.add_task(_run_merge, episode_id, project_id)
    return {"message": "Đang ghép video, vui lòng chờ..."}


@router.get("/{project_id}/episodes/{episode_id}/videos/merge")
async def get_merge_status(
    project_id: str,
    episode_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Kiểm tra trạng thái ghép video + trả URL nếu xong."""
    episode = await _get_owned_episode(episode_id, project_id, current_user, session)
    return {
        "status": episode.merged_video_status,  # None | merging | done | error
        "url": f"/data/{episode.merged_video_path}" if episode.merged_video_path else None,
        "error": episode.merged_video_error,
    }


@router.get("/{project_id}/episodes/{episode_id}/videos/download")
async def download_merged_video(
    project_id: str,
    episode_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Tải video đã ghép toàn tập."""
    episode = await _get_owned_episode(episode_id, project_id, current_user, session)
    if episode.merged_video_status != "done" or not episode.merged_video_path:
        raise HTTPException(404, "Video tập chưa sẵn sàng")
    path = DATA_DIR / episode.merged_video_path
    if not path.exists():
        raise HTTPException(404, "File không tồn tại")
    return FileResponse(
        path=str(path),
        media_type="video/mp4",
        filename=f"episode_{episode_id[:8]}.mp4",
    )

