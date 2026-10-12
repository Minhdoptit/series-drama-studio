# Phase 1 — Backend: DB Migration + APIs

**Status:** Pending  
**Effort:** ~1 ngày  
**Priority:** P1 — blocker cho Phase 2

---

## Context

- [`models.py`](file:///d:/Project/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/series-drama-studio/backend/app/models.py)
- [`api/scripts.py`](file:///d:/Project/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/series-drama-studio/backend/app/api/scripts.py)
- [`services/llm_service.py`](file:///d:/Project/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/series-drama-studio/backend/app/services/llm_service.py)

---

## Key Insights

- `Script` model hiện có `episode_id`, `title`, `content`, `prompt_used`, `created_at`
- Không có `version` hay `is_active` → không phân biệt phiên bản
- `Episode.script: Optional["Script"]` — SQLModel relationship chỉ trả 1 script (last)
- `PATCH /{project_id}/scenes/{scene_id}` đã có → chỉ cần thêm APIs mới

---

## Requirements

### Functional
- Script có `version` (số nguyên tăng dần), `is_active` (bool), `parent_id` (FK tự tham chiếu)
- Mỗi lần save → deactivate tất cả scripts cũ → insert script mới `is_active=True`
- `GET scripts` trả thêm `version`, `is_active`
- API `activate` → rollback một phiên bản cụ thể
- API `reparse-scenes` → parse lại content hiện tại → trả scenes mới (preview, chưa lưu)
- API confirm reparse → xóa scenes cũ của script, insert scenes mới

### Non-Functional
- Migration không mất data cũ
- `is_active=True` mặc định cho script cũ (trước migration)

---

## Architecture

```
Script (bảng hiện có + 3 field mới)
  ├── version: int = 1
  ├── is_active: bool = True     ← chỉ 1 script là active tại 1 thời điểm
  └── parent_id: Optional[str]   ← FK → scripts.id (bản trước đó)
```

**Invariant:** Với mỗi `episode_id`, chỉ có đúng 1 Script có `is_active = True`

---

## Related Files

| File | Action | Mô tả |
|------|--------|--------|
| `backend/app/models.py` | MODIFY | Thêm 3 field vào Script |
| `backend/app/api/scripts.py` | MODIFY | Sửa save + thêm 3 endpoints |
| `backend/migrate_script_versions.py` | CREATE | Migration script |

---

## Implementation Steps

### Step 1 — Thêm fields vào `models.py`

```python
class Script(SQLModel, table=True):
    __tablename__ = "scripts"

    id: str = Field(default_factory=gen_id, primary_key=True)
    episode_id: str = Field(foreign_key="episodes.id", index=True)
    title: Optional[str] = None
    content: str
    prompt_used: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # ─── Version tracking (mới) ───────────────────────────────────
    version: int = Field(default=1)
    is_active: bool = Field(default=True)
    parent_id: Optional[str] = Field(default=None, foreign_key="scripts.id")
    # ──────────────────────────────────────────────────────────────

    episode: Optional[Episode] = Relationship(back_populates="script")
    scenes: List["Scene"] = Relationship(back_populates="script")
```

### Step 2 — Migration script

Tạo file `backend/migrate_script_versions.py`:

```python
"""
Migration: Thêm version, is_active, parent_id vào bảng scripts
Chạy 1 lần: python migrate_script_versions.py
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    async with engine.begin() as conn:
        # Kiểm tra column đã tồn tại chưa
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='scripts' AND column_name='version'"
        ))
        if result.fetchone():
            print("✓ Already migrated")
            return

        await conn.execute(text("ALTER TABLE scripts ADD COLUMN version INTEGER NOT NULL DEFAULT 1"))
        await conn.execute(text("ALTER TABLE scripts ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        await conn.execute(text("ALTER TABLE scripts ADD COLUMN parent_id VARCHAR REFERENCES scripts(id)"))
        print("✓ Migration complete")

asyncio.run(migrate())
```

### Step 3 — Sửa `ScriptOut` model

```python
class ScriptOut(BaseModel):
    id: str
    episode_id: str
    title: Optional[str]
    content: str
    created_at: datetime
    version: int = 1          # ← thêm
    is_active: bool = True    # ← thêm
    scenes: List[SceneOut] = []
```

### Step 4 — Sửa endpoint `save_script` (đã có)

Trong `POST /scripts/save`:
```python
# Trước khi insert script mới: deactivate tất cả scripts cũ
await session.execute(
    update(Script)
    .where(Script.episode_id == episode_id)
    .values(is_active=False)
)

# Tính version mới
result_max = await session.execute(
    select(func.max(Script.version)).where(Script.episode_id == episode_id)
)
max_version = result_max.scalar() or 0

# Lấy id script hiện active để set parent_id
result_active = await session.execute(
    select(Script.id).where(Script.episode_id == episode_id, Script.is_active == True)
)
active_id = result_active.scalar_one_or_none()

# Insert script mới
script = Script(
    episode_id=episode_id,
    title=body.get("title"),
    content=body.get("content", ""),
    prompt_used=body.get("prompt_used"),
    version=max_version + 1,
    is_active=True,
    parent_id=active_id,  # trỏ về bản trước
)
```

### Step 5 — Thêm endpoint `PATCH activate` (rollback)

```python
@router.patch("/{project_id}/episodes/{episode_id}/scripts/{script_id}/activate")
async def activate_script(
    project_id: str, episode_id: str, script_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_project(project_id, current_user, session)
    await _get_episode(episode_id, project_id, session)

    # Kiểm tra script thuộc episode này
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
```

### Step 6 — Thêm endpoint `POST reparse-scenes` (preview)

```python
@router.post("/{project_id}/episodes/{episode_id}/scripts/{script_id}/reparse-scenes")
async def reparse_scenes(
    project_id: str, episode_id: str, script_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Parse lại scenes từ content của script, trả về preview (chưa lưu)."""
    await _get_project(project_id, current_user, session)
    result = await session.execute(
        select(Script).where(Script.id == script_id, Script.episode_id == episode_id)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Không tìm thấy kịch bản")

    # Gọi LLM service để parse lại scenes từ content text
    api_key_result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    api_config = api_key_result.scalar_one_or_none()
    if not api_config or not api_config.llm_key_enc:
        raise HTTPException(400, "Chưa cấu hình API key LLM")

    scenes = await parse_scenes_from_content(script.content, api_config)
    return {"scenes": scenes, "count": len(scenes)}
```

### Step 7 — Thêm endpoint `POST reparse-scenes/confirm` (apply)

```python
@router.post("/{project_id}/episodes/{episode_id}/scripts/{script_id}/reparse-scenes/confirm")
async def confirm_reparse(
    project_id: str, episode_id: str, script_id: str,
    body: dict,  # {"scenes": [...]}
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Xóa scenes cũ, insert scenes mới từ body."""
    await _get_project(project_id, current_user, session)
    result = await session.execute(
        select(Script).where(Script.id == script_id, Script.episode_id == episode_id)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Không tìm thấy kịch bản")

    # Xóa scenes cũ
    await session.execute(delete(Scene).where(Scene.script_id == script_id))

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
```

### Step 8 — Thêm `parse_scenes_from_content()` vào `llm_service.py`

Hàm này nhận `content: str` (kịch bản full text) → gửi lên LLM với prompt:
> "Hãy parse đoạn kịch bản sau thành JSON danh sách cảnh, mỗi cảnh gồm: scene_no, location, shot_type, duration_sec, action_desc, voice_over. Chỉ trả JSON."

---

## Todo List

- [ ] Thêm 3 fields vào `Script` model trong `models.py`
- [ ] Tạo `migrate_script_versions.py` và chạy thử
- [ ] Cập nhật `ScriptOut` pydantic model thêm `version`, `is_active`
- [ ] Sửa `save_script`: deactivate cũ, tính version, set parent_id
- [ ] Thêm import `update`, `func`, `delete` từ sqlalchemy vào scripts.py
- [ ] Thêm endpoint `PATCH .../scripts/{id}/activate`
- [ ] Thêm endpoint `POST .../scripts/{id}/reparse-scenes`
- [ ] Thêm endpoint `POST .../scripts/{id}/reparse-scenes/confirm`
- [ ] Thêm hàm `parse_scenes_from_content()` vào `llm_service.py`
- [ ] Test thủ công bằng curl hoặc FastAPI docs

---

## Success Criteria

- [ ] Script mới sau khi save có `version=N`, `is_active=True`; bản cũ có `is_active=False`
- [ ] `GET scripts` trả về field `version` và `is_active`
- [ ] `PATCH activate` đổi active script thành công
- [ ] `POST reparse-scenes` trả về JSON scenes hợp lệ
- [ ] `POST reparse-scenes/confirm` cập nhật scenes trong DB

---

## Risk Assessment

| Risk | Xác suất | Impact | Mitigation |
|------|----------|--------|------------|
| Migration fail nếu column đã tồn tại | Thấp | Thấp | Check trước khi ALTER |
| parse_scenes_from_content không parse đúng format user tự sửa | Trung bình | Trung bình | Trả lỗi rõ ràng, không crash, giữ cảnh cũ |
| Scenes có video đã gen bị xóa khi confirm reparse | Cao | Cao | Trả về warning count videos sẽ bị mồ côi |

---

## Next Steps

→ Phase 2: Frontend UI sau khi Phase 1 API sẵn sàng
