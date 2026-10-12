# Plan: Episode Layer — Quản lý kịch bản & ảnh theo Tập

**Trạng thái:** `pending`
**Ngày tạo:** 2026-07-23
**Ưu tiên:** Cao

---

## Mục tiêu
Thêm khái niệm **Tập (Episode)** vào giữa Project và Script/Image/Video,
cho phép quản lý nội dung theo từng tập phim trong 1 dự án series hoạt hình.

---

## Kiến trúc mới

```
Project
 ├── Episode[]          (tập 1, tập 2...)
 │    ├── Script        (1 tập = 1 kịch bản + scenes)
 │    │    └── Scene[] → Video[]
 │    └── Image[]       (ảnh riêng tập: bối cảnh, props, đạo cụ)
 ├── Image[]            (ảnh CHUNG cả series: nhân vật tái sử dụng)
 └── Document[]         (tài liệu tham khảo chung)
```

---

## Phase 1 — Backend: Data Model
**Status:** `[ ]`

### models.py
- [x] Thêm class `Episode`:
  ```python
  class Episode(SQLModel, table=True):
      __tablename__ = "episodes"
      id: str = Field(default_factory=gen_id, primary_key=True)
      project_id: str = Field(foreign_key="projects.id", index=True)
      ep_no: int
      title: str
      description: Optional[str] = None
      created_at: datetime = Field(default_factory=datetime.utcnow)
  ```
- [x] `Script`: đổi FK `project_id` → `episode_id`
- [x] `Image`: thêm `episode_id: Optional[str]` nullable
  - `None` = ảnh chung project (nhân vật)
  - `<id>` = ảnh riêng tập (bối cảnh, props)
- [x] `Project`: thêm `episodes: List["Episode"]` relationship

---

## Phase 2 — Backend: API Episodes
**Status:** `[ ]`

### [NEW] app/api/episodes.py
Prefix: `/projects/{project_id}/episodes`

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/` | Danh sách tập trong project |
| POST | `/` | Tạo tập mới (ep_no tự tăng) |
| GET | `/{ep_id}` | Chi tiết tập (kèm script nếu có) |
| PATCH | `/{ep_id}` | Cập nhật tên/mô tả tập |
| DELETE | `/{ep_id}` | Xoá tập (cascade xoá script/scene) |

### [MODIFY] app/api/scripts.py
- [x] Đổi prefix: `/projects/{project_id}/episodes/{ep_id}/scripts`
- [x] Thay `project_id` → `episode_id` trong query/create

### [MODIFY] app/api/images.py
- [x] Thêm query param `?shared=true` → ảnh chung project
- [x] Thêm query param `?episode_id=<id>` → ảnh theo tập
- [x] POST body thêm field `episode_id: Optional[str]`

### [MODIFY] app/api/videos.py
- [x] Thêm helper query list video theo episode

### [MODIFY] app/main.py
- [x] Register episodes router

---

## Phase 3 — Backend: Migration
**Status:** `[ ]`

### [NEW] backend/migrate_add_episodes.py
- [x] CREATE TABLE episodes
- [x] ALTER TABLE scripts: ADD `episode_id`, tạo Episode "Tập 1" auto cho mỗi script cũ
- [x] ALTER TABLE images: ADD `episode_id` nullable (mặc định null = ảnh chung)

---

## Phase 4 — Frontend: Routes
**Status:** `[ ]`

### [MODIFY] App.tsx
```
/dashboard                                 → list projects
/project/:projectId                        → ProjectDetail (list episodes)
/project/:projectId/episode/:epId/script   → ScriptStudio
/project/:projectId/episode/:epId/image    → ImageStudio (ảnh tập)
/project/:projectId/characters             → ImageStudio (nhân vật chung)
/project/:projectId/episode/:epId/video    → VideoStudio
/settings                                  → Settings
```
- [x] Bỏ `localStorage('activeProjectId')` — dùng route params thay thế

---

## Phase 5 — Frontend: Trang mới & cập nhật
**Status:** `[ ]`

### [NEW] pages/ProjectDetail.tsx
- [x] Header: tên project + nút "+ Tạo tập"
- [x] Tab `Các tập` / `Nhân vật chung`
- [x] Grid card episodes: số tập, tiêu đề, trạng thái (chưa có kịch bản / đã có / đã video)
- [x] Nút vào tập → navigate `/project/:id/episode/:epId/script`

### [MODIFY] pages/ScriptStudio.tsx
- [x] Đọc `projectId`, `epId` từ `useParams()`
- [x] Breadcrumb: Dự án > Tập X > Kịch bản

### [MODIFY] pages/ImageStudio.tsx
- [x] Nhận `episodeId` từ params (optional)
- [x] Toggle chế độ: ảnh chung / ảnh tập

### [MODIFY] pages/VideoStudio.tsx
- [x] Load scenes theo `epId` từ params

---

## Phase 6 — Frontend: Sidebar & Navigation
**Status:** `[ ]`

### [MODIFY] components/Layout/Sidebar.tsx
- [x] Hiển thị breadcrumb: tên project + tên tập active
- [x] Nav links cập nhật theo context hiện tại

---

## Quyết định đã chốt

| Câu hỏi | Quyết định |
|---|---|
| Ảnh nhân vật vs ảnh tập | 2 route riêng: `/characters` và `/episode/:id/image` |
| Migration scripts cũ | Tự tạo Episode "Tập 1" cho mỗi script |
| localStorage | Bỏ hoàn toàn — dùng URL params |

---

## Thứ tự thực hiện

```
Phase 1 (models) → Phase 2 (API) → Phase 3 (migration)
         ↓
Phase 4 (routes) → Phase 5 (pages) → Phase 6 (sidebar)
```

Ước tính: ~4-6h implement đầy đủ
