from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_session
from app.models import Episode, Project, User
from app.services.auth_service import get_current_user
from app.services.cascade_service import delete_episode_cascade

router = APIRouter()


class EpisodeCreate(BaseModel):
    title: str
    description: Optional[str] = None


class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class EpisodeResponse(BaseModel):
    id: str
    project_id: str
    ep_no: int
    title: str
    description: Optional[str]
    created_at: datetime
    has_script: bool = False  # convenience flag cho FE


async def _get_project_or_404(
    project_id: str, user: User, session: AsyncSession
) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Không tìm thấy dự án")
    return project


async def _get_episode_or_404(
    episode_id: str, project_id: str, session: AsyncSession
) -> Episode:
    result = await session.execute(
        select(Episode).where(
            Episode.id == episode_id,
            Episode.project_id == project_id,
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(404, "Không tìm thấy tập")
    return ep


@router.get("/{project_id}/episodes", response_model=list[EpisodeResponse])
async def list_episodes(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project_or_404(project_id, current_user, session)

    result = await session.execute(
        select(Episode)
        .where(Episode.project_id == project_id)
        .order_by(Episode.ep_no)
    )
    episodes = result.scalars().all()

    # Lấy danh sách episode_id có script
    from app.models import Script
    script_result = await session.execute(
        select(Script.episode_id).where(
            Script.episode_id.in_([ep.id for ep in episodes])
        )
    )
    ep_ids_with_script = {row[0] for row in script_result.all()}

    return [
        EpisodeResponse(
            id=ep.id,
            project_id=ep.project_id,
            ep_no=ep.ep_no,
            title=ep.title,
            description=ep.description,
            created_at=ep.created_at,
            has_script=ep.id in ep_ids_with_script,
        )
        for ep in episodes
    ]


@router.post("/{project_id}/episodes", response_model=EpisodeResponse, status_code=201)
async def create_episode(
    project_id: str,
    body: EpisodeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project_or_404(project_id, current_user, session)

    # Tự tăng ep_no
    result = await session.execute(
        select(Episode)
        .where(Episode.project_id == project_id)
        .order_by(Episode.ep_no.desc())
    )
    last = result.scalars().first()
    next_no = (last.ep_no + 1) if last else 1

    ep = Episode(project_id=project_id, ep_no=next_no, **body.model_dump())
    session.add(ep)
    await session.commit()
    await session.refresh(ep)

    return EpisodeResponse(
        id=ep.id,
        project_id=ep.project_id,
        ep_no=ep.ep_no,
        title=ep.title,
        description=ep.description,
        created_at=ep.created_at,
        has_script=False,
    )


@router.get("/{project_id}/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    project_id: str,
    episode_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project_or_404(project_id, current_user, session)
    ep = await _get_episode_or_404(episode_id, project_id, session)

    from app.models import Script
    sr = await session.execute(
        select(Script.id).where(Script.episode_id == ep.id)
    )
    has_script = sr.scalar_one_or_none() is not None

    return EpisodeResponse(
        id=ep.id,
        project_id=ep.project_id,
        ep_no=ep.ep_no,
        title=ep.title,
        description=ep.description,
        created_at=ep.created_at,
        has_script=has_script,
    )


@router.patch("/{project_id}/episodes/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    project_id: str,
    episode_id: str,
    body: EpisodeUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project_or_404(project_id, current_user, session)
    ep = await _get_episode_or_404(episode_id, project_id, session)

    for k, v in body.model_dump(exclude_none=True).items():
        setattr(ep, k, v)

    session.add(ep)
    await session.commit()
    await session.refresh(ep)

    return EpisodeResponse(
        id=ep.id,
        project_id=ep.project_id,
        ep_no=ep.ep_no,
        title=ep.title,
        description=ep.description,
        created_at=ep.created_at,
        has_script=False,
    )


@router.delete("/{project_id}/episodes/{episode_id}", status_code=204)
async def delete_episode(
    project_id: str,
    episode_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project_or_404(project_id, current_user, session)
    ep = await _get_episode_or_404(episode_id, project_id, session)

    # Cascade: script + scenes + videos + ảnh riêng tập (kèm file trên đĩa)
    await delete_episode_cascade(session, ep)
    await session.commit()

