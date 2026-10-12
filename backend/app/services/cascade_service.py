"""
Xoá dữ liệu theo tầng (cascade).

Các quan hệ trong models.py không khai báo cascade và khoá ngoại không có
ON DELETE CASCADE, nên xoá bản ghi cha khi vẫn còn bản ghi con sẽ gây
IntegrityError (HTTP 500). Module này xoá con trước cha theo đúng thứ tự,
đồng thời dọn luôn file trên đĩa để không để lại rác.

Thứ tự phụ thuộc:
    Project → Episode → Script → Scene → Video
    Project → Image (episode_id = NULL)
    Episode → Image (episode_id = <id>)
    Project → Document
"""
import os
import pathlib
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Document, Episode, Image, Project, Scene, Script, Video

DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))


def _unlink_quietly(rel_path: str | None, base: pathlib.Path = DATA_DIR) -> None:
    """Xoá file trên đĩa, bỏ qua mọi lỗi (file đã mất, đang bị khoá...)."""
    if not rel_path:
        return
    try:
        p = base / rel_path
        if p.exists():
            p.unlink()
    except Exception:
        pass


async def delete_videos_of_scenes(session: AsyncSession, scene_ids: Sequence[str]) -> int:
    """Xoá tất cả Video thuộc các scene đã cho (kèm file mp4). Trả về số bản ghi đã xoá."""
    if not scene_ids:
        return 0
    res = await session.execute(select(Video).where(Video.scene_id.in_(list(scene_ids))))
    videos = res.scalars().all()
    for v in videos:
        _unlink_quietly(v.file_path)
        await session.delete(v)
    return len(videos)


async def delete_scenes_of_script(session: AsyncSession, script_id: str) -> None:
    """Xoá toàn bộ Scene của một Script, xoá Video con trước."""
    res = await session.execute(select(Scene).where(Scene.script_id == script_id))
    scenes = res.scalars().all()
    await delete_videos_of_scenes(session, [s.id for s in scenes])
    for s in scenes:
        await session.delete(s)


async def delete_episode_cascade(session: AsyncSession, episode: Episode) -> None:
    """Xoá một Episode cùng scripts, scenes, videos, ảnh riêng tập và video đã ghép."""
    scripts_res = await session.execute(select(Script).where(Script.episode_id == episode.id))
    for script in scripts_res.scalars().all():
        await delete_scenes_of_script(session, script.id)
        await session.delete(script)

    # Ảnh riêng của tập (bối cảnh, đạo cụ) — FK images.episode_id
    imgs_res = await session.execute(select(Image).where(Image.episode_id == episode.id))
    for img in imgs_res.scalars().all():
        _unlink_quietly(img.file_path)
        await session.delete(img)

    _unlink_quietly(episode.merged_video_path)
    await session.delete(episode)


async def delete_project_cascade(session: AsyncSession, project: Project) -> None:
    """Xoá một Project cùng toàn bộ episodes, ảnh chung và tài liệu."""
    eps_res = await session.execute(select(Episode).where(Episode.project_id == project.id))
    for ep in eps_res.scalars().all():
        await delete_episode_cascade(session, ep)

    # Ảnh còn lại của project (ảnh nhân vật chung, episode_id IS NULL)
    imgs_res = await session.execute(select(Image).where(Image.project_id == project.id))
    for img in imgs_res.scalars().all():
        _unlink_quietly(img.file_path)
        await session.delete(img)

    docs_res = await session.execute(select(Document).where(Document.project_id == project.id))
    for doc in docs_res.scalars().all():
        # Bản ghi cũ/mới lưu path khác gốc — dùng resolver chung của documents.py
        from app.api.documents import resolve_document_path
        try:
            p = resolve_document_path(doc.file_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass
        await session.delete(doc)

    await session.delete(project)
