from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """
    Thời điểm UTC hiện tại, dạng naive (không kèm tzinfo).

    datetime.utcnow() đã deprecated từ Python 3.12. Các cột DateTime ở đây không
    có timezone nên phải bỏ tzinfo, nếu không sẽ lệch với dữ liệu đã lưu.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─── Enums ───────────────────────────────────────────────

class ImageType(str, Enum):
    character = "character"
    background = "background"
    prop = "prop"


class VideoStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class DocumentType(str, Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"
    md = "md"


class AIProvider(str, Enum):
    gemini = "gemini"
    openai = "openai"
    kling = "kling"
    runway = "runway"


# ─── User ────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=gen_id, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow)

    projects: List["Project"] = Relationship(back_populates="user")
    api_key: Optional["ApiKey"] = Relationship(back_populates="user")


# ─── Project ─────────────────────────────────────────────

class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str
    style: Optional[str] = None          # e.g. "3D Pixar mềm"
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    user: Optional[User] = Relationship(back_populates="projects")
    episodes: List["Episode"] = Relationship(back_populates="project")
    # ảnh chung cả series (nhân vật, dùng lại nhiều tập)
    images: List["Image"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"primaryjoin": "and_(Image.project_id == Project.id, Image.episode_id == None)"},
    )
    documents: List["Document"] = Relationship(back_populates="project")


# ─── Episode ─────────────────────────────────────────────

class Episode(SQLModel, table=True):
    __tablename__ = "episodes"

    id: str = Field(default_factory=gen_id, primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    ep_no: int                            # số thứ tự tập
    title: str                            # "Tập 1 — Ngày đầu tiên"
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    # merged video (ghep tap)
    merged_video_path: Optional[str] = None
    merged_video_status: Optional[str] = None
    merged_video_error: Optional[str] = None

    project: Optional[Project] = Relationship(back_populates="episodes")
    scripts: List["Script"] = Relationship(back_populates="episode")
    # ảnh riêng tập: bối cảnh, props, đạo cụ
    images: List["Image"] = Relationship(back_populates="episode")


# ─── Script + Scene ──────────────────────────────────────

class Script(SQLModel, table=True):
    __tablename__ = "scripts"

    id: str = Field(default_factory=gen_id, primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    episode_id: str = Field(foreign_key="episodes.id", index=True)
    title: Optional[str] = None
    content: str                          # full script text
    prompt_used: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    # ─── Version tracking ────────────────────────────────────────
    version: int = Field(default=1)
    is_active: bool = Field(default=True)
    parent_id: Optional[str] = Field(default=None, foreign_key="scripts.id")
    # ─────────────────────────────────────────────────────────────

    episode: Optional[Episode] = Relationship(back_populates="scripts")
    scenes: List["Scene"] = Relationship(back_populates="script")


class Scene(SQLModel, table=True):
    __tablename__ = "scenes"

    id: str = Field(default_factory=gen_id, primary_key=True)
    script_id: str = Field(foreign_key="scripts.id", index=True)
    scene_no: int
    location: Optional[str] = None
    action_desc: Optional[str] = None
    shot_type: Optional[str] = None
    duration_sec: Optional[float] = None
    voice_over: Optional[str] = None
    image_id: Optional[str] = Field(default=None, foreign_key="images.id")
    image_ids: Optional[str] = Field(default=None)    # JSON string e.g. '["id1", "id2"]'
    extra_prompt: Optional[str] = None    # user thêm prompt khi gen video

    script: Optional[Script] = Relationship(back_populates="scenes")
    image: Optional["Image"] = Relationship()
    videos: List["Video"] = Relationship(back_populates="scene")


# ─── Image ───────────────────────────────────────────────

class Image(SQLModel, table=True):
    __tablename__ = "images"

    id: str = Field(default_factory=gen_id, primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    episode_id: Optional[str] = Field(default=None, foreign_key="episodes.id", index=True)
    # episode_id = None  → ảnh chung project (nhân vật)
    # episode_id = <id>  → ảnh riêng tập (bối cảnh, props)

    type: ImageType = ImageType.character
    label: Optional[str] = None           # "Hươu con", "Sảnh đăng ký"...
    prompt: Optional[str] = None
    style: Optional[str] = None
    file_path: str                         # relative to DATA_DIR
    thumbnail_path: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    project: Optional[Project] = Relationship(back_populates="images")
    episode: Optional[Episode] = Relationship(back_populates="images")


# ─── Video ───────────────────────────────────────────────

class Video(SQLModel, table=True):
    __tablename__ = "videos"

    id: str = Field(default_factory=gen_id, primary_key=True)
    scene_id: str = Field(foreign_key="scenes.id", index=True)
    file_path: Optional[str] = None
    status: VideoStatus = VideoStatus.pending
    prompt_used: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None        # khi bắt đầu gen (running)
    completed_at: Optional[datetime] = None

    scene: Optional[Scene] = Relationship(back_populates="videos")


# ─── Document ────────────────────────────────────────────

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=gen_id, primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    file_name: str
    file_path: str
    file_type: DocumentType
    extracted_text: Optional[str] = None
    token_count: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)

    project: Optional[Project] = Relationship(back_populates="documents")


# ─── ApiKey ──────────────────────────────────────────────

class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", unique=True, index=True)

    llm_provider: Optional[str] = "gemini"
    llm_model: Optional[str] = "gemini-2.0-flash"
    llm_key_enc: Optional[str] = None        # encrypted

    image_provider: Optional[str] = "gemini"
    image_model: Optional[str] = "imagen-3"
    image_key_enc: Optional[str] = None      # encrypted

    video_provider: Optional[str] = "kling"
    video_model: Optional[str] = "kling-v2-master"
    video_key_enc: Optional[str] = None      # encrypted

    updated_at: datetime = Field(default_factory=utcnow)

    user: Optional[User] = Relationship(back_populates="api_key")
