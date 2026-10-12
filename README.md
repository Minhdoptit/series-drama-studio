# Series Drama Studio

App nội bộ tự động sản xuất **phim hoạt hình ngắn nhiều tập** bằng AI: nhập kịch bản → sinh tạo hình nhân vật/bối cảnh → chia cảnh → dựng video từng cảnh → ghép bản nháp cả tập.

Định dạng đầu ra: mỗi tập 45–60 giây, khung dọc 9:16, phong cách 3D mềm kiểu Pixar. Sản phẩm cuối là **nguyên liệu** (ảnh + video từng cảnh) kèm một bản ghép nháp để dựng hoàn thiện ở CapCut/Premiere.

Toàn bộ giao diện tiếng Việt. Chạy nội bộ qua trình duyệt, nhiều người trong cùng mạng LAN dùng được, mỗi user tự cắm API key riêng.

---

## Mục lục

- [Tính năng](#tính-năng)
  - [1. Tài khoản & phân quyền](#1-tài-khoản--phân-quyền)
  - [2. Quản lý dự án & tập phim](#2-quản-lý-dự-án--tập-phim)
  - [3. Studio Kịch Bản](#3-studio-kịch-bản)
  - [4. Ảnh: nhân vật chung vs. ảnh riêng tập](#4-ảnh-nhân-vật-chung-vs-ảnh-riêng-tập)
  - [5. Studio Video](#5-studio-video)
  - [6. Cài đặt API](#6-cài-đặt-api)
  - [7. Bảo đảm ở tầng hệ thống](#7-bảo-đảm-ở-tầng-hệ-thống)
- [Công nghệ](#công-nghệ)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Mô hình dữ liệu](#mô-hình-dữ-liệu)
- [Luồng làm việc](#luồng-làm-việc)
- [AI providers](#ai-providers)
- [Cài đặt & chạy](#cài-đặt--chạy)
- [Biến môi trường](#biến-môi-trường)
- [Migration & script tiện ích](#migration--script-tiện-ích)
- [API endpoints](#api-endpoints)
- [Lưu ý & hạn chế đã biết](#lưu-ý--hạn-chế-đã-biết)

---

## Tính năng

Tổng quan các màn hình:

| Màn hình | Route | Chức năng |
|---|---|---|
| **Đăng nhập / Đăng ký** | `/login`, `/register` | Tài khoản riêng cho từng người, mỗi người tự cắm API key |
| **Dashboard** | `/dashboard` | Danh sách project (series), tạo/xoá |
| **Chi tiết dự án** | `/project/:projectId` | Quản lý danh sách tập (episodes) + tab nhân vật chung |
| **Studio Kịch Bản** | `/project/:projectId/episode/:epId/script` | Upload tài liệu → gen kịch bản → bóc bảng cảnh, quản lý phiên bản |
| **Nhân Vật Chung** | `/project/:projectId/characters` | Gen & lưu ảnh nhân vật dùng lại xuyên suốt mọi tập |
| **Studio Hình Ảnh** | `/project/:projectId/episode/:epId/image` | Gen ảnh bối cảnh / đạo cụ riêng cho tập |
| **Studio Video** | `/project/:projectId/episode/:epId/video` | Gán ảnh vào cảnh → gen video hàng loạt → ghép cả tập |
| **Cài đặt API** | `/settings` | Chọn provider + model + key cho LLM / Image / Video |

---

### 1. Tài khoản & phân quyền

- Đăng ký bằng email + mật khẩu + họ tên, **tự đăng nhập luôn** sau khi đăng ký (API trả token ngay).
- Mật khẩu hash bằng bcrypt; token JWT hạn 7 ngày (cấu hình qua `ACCESS_TOKEN_EXPIRE_MINUTES`).
- Token và thông tin user lưu ở 2 cookie `ds_token` / `ds_user` (TTL 7 ngày, `SameSite=Strict`), đọc đồng bộ ngay khi khởi tạo store nên **F5 không bị bật ra ngoài**.
- Axios interceptor tự gắn header `Authorization`; gặp `401` thì xoá cookie và chuyển về `/login`. Route lạ chuyển về `/dashboard`.
- **Mọi endpoint đều kiểm tra quyền sở hữu** — không thể đọc/sửa project, tập, cảnh, ảnh, video của user khác (kể cả khi biết ID). Ví dụ gen video chỉ nhận `scene_id` thuộc project của mình.
- Sidebar hiện avatar viết tắt từ họ tên (hoặc email), bấm vào để đăng xuất; menu điều hướng đổi theo ngữ cảnh (đang ở dự án nào, tập nào).

### 2. Quản lý dự án & tập phim

- Grid card dự án: tên, phong cách hình ảnh, mô tả, ngày cập nhật (định dạng `vi-VN`).
- Modal tạo dự án điền sẵn phong cách mặc định *"3D Pixar mềm, nhân vật con vật cách điệu dáng người"* — chỉ cần đặt tên là xong.
- Có empty state riêng và error state kèm nút **Thử lại** khi không gọi được backend.
- Trong dự án: 2 tab **Các tập phim** (kèm số lượng) và **Nhân vật chung**.
- Card mỗi tập hiện số thứ tự (`ep_no` tự tăng theo tập lớn nhất hiện có), tiêu đề, mô tả, badge **Có kịch bản / Chưa có kịch bản**, và 3 nút tắt sang Kịch bản · Hình ảnh · Video.
- Thêm tập nhanh bằng modal (gõ tên rồi Enter). Xoá tập/dự án có hộp thoại xác nhận nói rõ dữ liệu con cũng mất.

### 3. Studio Kịch Bản

**Nhập liệu**

- Phong cách hình ảnh (text tự do), thời lượng mục tiêu bằng **slider 20–180 giây** (bước 5s).
- **Danh sách nhân vật động**: mỗi dòng tên / tuổi / mô tả ngắn, thêm và xoá từng dòng.
- Nội dung tập: mô tả tình tiết, cảm xúc muốn truyền tải.

**Tài liệu tham khảo**

- Kéo–thả hoặc chọn **nhiều file cùng lúc**: PDF, DOCX, TXT, MD.
- Backend bóc text ngay khi upload (pdfplumber / python-docx) và trả về **số token ước lượng** (~4 ký tự = 1 token).
- Tick chọn tài liệu nào được nhồi vào prompt; tổng token hiện realtime và **cảnh báo đỏ khi vượt 100.000 token** ("AI sẽ chỉ đọc phần đầu").
- Xoá tài liệu khỏi danh sách bất kỳ lúc nào.

**Gen & chỉnh sửa**

- Bấm *Gen Kịch Bản* → LLM trả về `{ title, content, scenes[] }`, toast báo số cảnh bóc được.
- Nếu chưa cắm API key, toast báo lỗi kèm **link bấm được để sang thẳng trang Cài đặt** (hiện 6 giây).
- Nội dung kịch bản sửa trực tiếp trong textarea; hiện badge `v{số phiên bản}` và badge **"✏️ chưa lưu"** khi có thay đổi. Nút *Lưu kịch bản* chỉ xuất hiện khi thực sự có gì để lưu.

**Phiên bản & đồng bộ cảnh**

- Dropdown **Lịch sử (n)** liệt kê mọi phiên bản kèm thời gian tạo; bản đang dùng có badge `● active`, click bản cũ để **khôi phục (rollback)**.
- Sau khi lưu, modal hỏi có cập nhật danh sách cảnh theo nội dung mới không, **cảnh báo rõ** cảnh cũ (kể cả cảnh đã gán ảnh) sẽ bị thay thế.
- Chọn cập nhật → AI bóc lại cảnh → **hiện preview** (số cảnh, địa điểm, thời lượng từng cảnh) → chỉ ghi vào DB khi bấm xác nhận. Bấm *Không, giữ cảnh cũ* thì dữ liệu cảnh không bị đụng tới.

**Bảng cảnh**

- Mỗi dòng: số cảnh, địa điểm, cỡ/góc máy, thời lượng. Click để mở rộng xem mô tả hành động và **thoại (🎙)**.

### 4. Ảnh: nhân vật chung vs. ảnh riêng tập

Cùng một màn hình dùng cho 2 phạm vi khác nhau:

| Phạm vi | Route | Lưu với | Dùng để |
|---|---|---|---|
| **Chung cả series** | `/characters` | `episode_id = NULL` | Nhân vật — dùng lại ở mọi tập, giữ nhất quán diện mạo |
| **Riêng từng tập** | `/episode/:epId/image` | `episode_id = <id tập>` | Bối cảnh, đạo cụ chỉ xuất hiện trong tập đó |

- 3 loại ảnh: **Nhân vật · Bối cảnh · Đạo cụ**, mỗi loại có badge riêng trong thư viện.
- **Bắt buộc đặt tên ảnh trước khi lưu** — tên này chính là nhãn hiện trong picker lúc ghép ảnh vào cảnh, và được đưa vào prompt video ("Ảnh #1 (Hươu con)").
- 5 preset phong cách: 3D Pixar mềm · Anime Ghibli · 2D cartoon · Watercolor · Semi-realistic 3D.
- Mỗi lần gen ra **3 phương án** để chọn, có nút *Gen lại* nếu chưa hài lòng; lưu từng ảnh vừa ý vào thư viện.
- Thư viện: grid thumbnail, **đổi tên inline** (Enter để lưu, Escape để huỷ), xoá ảnh.
- Chuyển sang tập khác thì thư viện tự tải lại theo đúng phạm vi tập đó.
- Prompt gửi provider được ghép thêm hậu tố cố định: *"Phong cách: … Nền xám studio. Chất lượng cao, 3D render."*
- Backend còn nhận `reference_image_ids` để gen ảnh mới dựa trên ảnh đã lưu (đọc file → base64 → gửi kèm cho provider). **UI hiện chưa có chỗ chọn ảnh tham chiếu này** — chỉ gọi được qua API.

### 5. Studio Video

**Chuẩn bị cảnh**

- Chọn kịch bản nếu tập có nhiều phiên bản.
- Checkbox từng cảnh + **Chọn tất cả**, hiện "Đã chọn x/y cảnh".
- **Gán nhiều ảnh tham chiếu cho một cảnh**: modal grid 4 cột tỉ lệ 9:16, tick chọn nhiều nhân vật/bối cảnh, có *Bỏ chọn tất cả*, nút xác nhận hiện số ảnh đã chọn. Ảnh đã gán hiện thumbnail nhỏ ngay trong dòng cảnh kèm nhãn, mỗi ảnh có nút `×` để bỏ riêng lẻ.
- **Prompt phụ cho từng cảnh**: input inline, tự lưu lên server sau 600ms ngừng gõ (debounce) — không cần bấm lưu.

**Tuỳ chọn xuất**

- 5 preset tỉ lệ + độ phân giải: `9:16 720p` · `9:16 1080p` · `16:9 720p` · `16:9 4K` · `1:1 720p`. Nhãn ghi rõ độ phân giải vì với Veo **giá tính theo giây phụ thuộc độ phân giải**.
- Thời lượng 5s hoặc 10s. Nếu provider đang chọn là Gemini/Veo, UI **tự lock 8s** (Veo chỉ hỗ trợ 8 giây).

**Gen & theo dõi**

- Bấm gen → hộp thoại xác nhận số cảnh (vì **gọi AI tốn tiền thật**) → backend trả `202` kèm danh sách `video_ids`, task chạy ngầm.
- Poll trạng thái mỗi 5 giây tới khi mọi video kết thúc, sau đó toast tổng số video xong.
- **Reload trang không mất theo dõi**: khi mở lại, FE quét video còn `pending`/`running` và tự poll tiếp.
- Mỗi cảnh đang gen hiện **đồng hồ đếm giây** (tính từ `started_at`, cập nhật mỗi giây) và progress bar ước lượng theo mốc 3 phút (chặn ở 92% để không hiện 100% khi chưa xong).
- Trạng thái: `⏳ Chờ gen` → `⚡ Đang gen` → xong / lỗi. Lỗi hiện **thông báo tiếng Việt** cắt còn 50 ký tự, hover xem đầy đủ.
- Xong: **player nhúng ngay trong dòng cảnh** + nút Xem và nút Tải video cảnh đó.

**Ghép tập**

- Bấm *Ghép Tập* → xác nhận số video → ffmpeg concat chạy ngầm → poll 5 giây/lần.
- Xong: banner xanh có player xem trước + nút **Tải toàn tập** (`episode_xxxxxxxx.mp4`). Lỗi: banner đỏ kèm lý do cụ thể.
- Trạng thái ghép được lưu ở DB (`merged_video_status`) nên mở lại trang vẫn thấy kết quả lần ghép trước.
- Mọi interval/timeout được dọn khi rời trang — không rò rỉ request nền.

### 6. Cài đặt API

- 3 nhóm độc lập: **LLM (gen kịch bản)** · **Image AI** · **Video AI**; mỗi nhóm chọn provider, model và key riêng.
- Danh sách provider/model **lấy động từ backend** (`GET /settings/models`, nguồn là `LLM_MODELS`/`IMAGE_MODELS`/`VIDEO_MODELS` trong tầng service) — không hardcode ở frontend, tránh chào model mà backend không gọi được.
- Đổi provider thì model tự nhảy về lựa chọn hợp lệ đầu tiên của provider đó.
- Nút **Kiểm tra** gọi thật lên provider để xác thực key: Gemini / OpenAI / MiniMax / GLM kiểm qua endpoint list models; Kling / Runway chỉ xác nhận đã lưu (sẽ kiểm khi gen video thật).
- Test được **key đã lưu mà không cần nhập lại** — FE gửi sentinel `___saved___`, backend tự giải mã key trong DB.
- Ô key dạng `password`, có badge **Key đã lưu**, để trống nếu không muốn đổi. API **chỉ trả cờ `*_key_set`**, không bao giờ trả key ra ngoài.
- Video AI dùng Gemini/Veo mà chưa cắm key riêng thì **tự fallback sang key của Image AI** (cùng một Gemini API key).

### 7. Bảo đảm ở tầng hệ thống

- **Ảnh mẫu thật sự được dùng khi dựng video** — mỗi cảnh lưu `image_ids`, ảnh được đọc từ đĩa và gửi đúng định dạng từng provider yêu cầu (base64 hoặc URL), kèm nhãn nhân vật trong prompt.
- **Version kịch bản** — mỗi lần lưu tạo bản mới (`version`, `parent_id`), chỉ một bản `is_active`; rollback không mất bản nào.
- **Việc lâu chạy ngầm, báo khi xong** — gen video và ghép tập chạy qua `BackgroundTasks`, FE poll `pending → running → done | error`.
- **Chống task mồ côi** — video còn `running` khi backend restart được reset thành `error` với lý do rõ ràng ngay lúc khởi động, không treo mãi.
- **Tự dọn rác** — mỗi cảnh chỉ giữ tối đa **2 video mới nhất**, xoá cả bản ghi DB lẫn file mp4 (chạy khi gen mới và lúc khởi động).
- **API key mã hoá** — Fernet ciphertext trong DB; app **fail-fast** ngay khi khởi động nếu `ENCRYPTION_KEY` thiếu/sai định dạng hoặc `SECRET_KEY` ngắn hơn 32 ký tự.
- **Xoá theo tầng** — `cascade_service.py` xoá con trước cha đúng thứ tự và dọn file trên đĩa (FK không có `ON DELETE CASCADE`).
- **CORS whitelist** — khai báo qua `CORS_ORIGINS`, không dùng `*` kèm `allow_credentials`.
- **Lỗi tiếng Việt cho người dùng, traceback cho dev** — lỗi gọi AI được log kèm provider + model ở server, còn client nhận thông báo đọc được thay vì "Internal Server Error".
- **Sao lưu = copy thư mục** — toàn bộ ảnh/video/tài liệu nằm gọn trong `data/`.

---

## Công nghệ

**Backend** — Python 3.12+ / FastAPI 0.115 · SQLModel + SQLAlchemy async · PostgreSQL 16 (driver `psycopg` v3) · JWT (`python-jose`) + bcrypt · Fernet (`cryptography`) · httpx · pdfplumber + python-docx · ffmpeg (CLI, để ghép video)

**Frontend** — React 18 + TypeScript + Vite 5 · React Router 7 · TanStack Query 5 · Zustand (auth store) · axios · react-hot-toast · react-dropzone · lucide-react

**Hạ tầng** — Docker Compose (db + backend + frontend/nginx)

---

## Cấu trúc thư mục

```
series-drama-studio/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, mount /data, lifespan (reset zombie video + cleanup)
│   │   ├── database.py              # async engine + session factory
│   │   ├── models.py                # SQLModel: User, Project, Episode, Script, Scene, Image, Video, Document, ApiKey
│   │   ├── api/                     # routers
│   │   │   ├── auth.py              # register / login / me
│   │   │   ├── projects.py          # CRUD project
│   │   │   ├── episodes.py          # CRUD tập
│   │   │   ├── scripts.py           # gen/save kịch bản, version, scene, re-parse
│   │   │   ├── documents.py         # upload & bóc text tài liệu
│   │   │   ├── images.py            # gen/save/list/xoá ảnh
│   │   │   ├── videos.py            # gen video (background), status, download, merge tập
│   │   │   └── settings.py          # API key per-user, test key, danh sách model
│   │   ├── services/
│   │   │   ├── auth_service.py      # hash password, JWT, get_current_user
│   │   │   ├── encryption_service.py# Fernet encrypt/decrypt API key (fail-fast nếu key sai)
│   │   │   ├── llm_service.py       # gen kịch bản: Gemini / OpenAI / Claude / MiniMax / GLM
│   │   │   ├── image_service.py     # gen ảnh: Imagen / DALL-E / MiniMax / CogView-GLM
│   │   │   ├── video_service.py     # gen video: Kling / Runway / CogVideoX / Veo 3.x + concat ffmpeg
│   │   │   ├── document_service.py  # extract text PDF/DOCX/TXT/MD + đếm token
│   │   │   └── cascade_service.py   # xoá theo tầng + dọn file
│   │   └── workers/
│   ├── migrate_*.py                 # migration thủ công (xem mục bên dưới)
│   ├── seed.py                      # tạo user test
│   ├── check_schema.py              # in schema thực tế trong DB
│   ├── test_system.py, test_veo3.py, test_glm_flow.py
│   ├── run.py                       # entrypoint Windows-safe (SelectorEventLoop cho psycopg)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # routes + PrivateRoute + QueryClient
│   │   ├── pages/                   # Login, Register, Dashboard, ProjectDetail, ScriptStudio, ImageStudio, VideoStudio, Settings
│   │   ├── components/Layout/       # AppLayout, Sidebar
│   │   ├── components/ScriptStudio/ # DocumentUpload
│   │   ├── store/authStore.ts       # token trong cookie ds_token
│   │   └── lib/api.ts               # axios instance + interceptor 401 → /login
│   ├── package.json
│   └── Dockerfile                   # build Vite → nginx serve SPA
├── data/                            # KHÔNG commit (đã gitignore)
│   ├── uploads/                     # tài liệu user upload
│   ├── assets/                      # ảnh đã gen
│   ├── videos/                      # video từng cảnh + bản ghép tập
│   ├── thumbnails/
│   └── postgres/                    # volume DB khi chạy Docker
├── docs/
│   ├── design-process.md
│   ├── episode-template.md
│   ├── specs/co-vua-10-tap-spec.md
│   └── plans/
├── docker-compose.yml
└── .env.example
```

Thư mục `data/` được mount static tại `GET /data/...` để frontend load ảnh/video trực tiếp.

---

## Mô hình dữ liệu

```
User ──1:N── Project ──1:N── Episode ──1:N── Script (nhiều version, 1 active)
  │             │                │                 └──1:N── Scene ──1:N── Video
  │             ├──1:N── Image (episode_id = NULL → ảnh chung series: nhân vật)
  │             │        Image (episode_id = <id>  → ảnh riêng tập: bối cảnh, đạo cụ)
  │             └──1:N── Document
  └──1:1── ApiKey (llm / image / video: provider + model + key đã mã hoá)
```

Ghi chú các cột đáng lưu ý:

| Bảng | Cột | Ý nghĩa |
|---|---|---|
| `scripts` | `version`, `is_active`, `parent_id` | Lịch sử phiên bản kịch bản; chỉ 1 bản active mỗi tập |
| `scenes` | `image_ids` | JSON array id ảnh gắn vào cảnh (`image_id` là cột cũ, giữ để tương thích) |
| `scenes` | `extra_prompt` | Prompt user thêm khi gen video cho riêng cảnh đó |
| `episodes` | `merged_video_path/_status/_error` | Kết quả ghép nháp cả tập |
| `videos` | `status`, `started_at`, `completed_at`, `error_msg` | Theo dõi task chạy ngầm |
| `documents` | `extracted_text`, `token_count` | Text đã bóc, dùng làm context cho LLM |

Bảng được tạo tự động bằng `SQLModel.metadata.create_all` khi backend khởi động.

---

## Luồng làm việc

```
1. Đăng ký / đăng nhập          → JWT (7 ngày), lưu cookie ds_token
2. Cài đặt → cắm API key        → mã hoá Fernet, lưu DB
3. Tạo Project (series)         → đặt tên + phong cách chung
4. Tạo Episode (tập)
5. Script Studio
   ├─ upload tài liệu           → bóc text (pdfplumber / python-docx)
   ├─ POST scripts/generate     → LLM trả JSON { content, scenes[] }
   ├─ POST scripts/save         → tạo version mới + ghi Scene
   └─ sửa cảnh / re-parse       → PATCH scene, hoặc nhờ LLM bóc lại scene list
6. Ảnh
   ├─ Nhân vật (chung series)   → gen 3 phương án → chọn, đặt tên & lưu
   └─ Bối cảnh/đạo cụ (theo tập)→ lưu kèm episode_id, chỉ dùng trong tập đó
7. Video Studio
   ├─ gắn ảnh vào từng cảnh     → scenes.image_ids
   ├─ POST videos/generate      → 202 + BackgroundTask mỗi cảnh
   │                              prompt = shot_type + action + location + extra_prompt
   │                              + ảnh tham chiếu + style 9:16
   ├─ poll GET videos/{id}      → pending → running → done | error
   ├─ POST episodes/{id}/videos/merge → ffmpeg concat → bản nháp cả tập
   └─ download từng cảnh hoặc bản ghép
```

Tuỳ chọn khi gen video: `video_size` ∈ `720x1280`, `1280x720`, `1024x1024`, `1080x1920`, `2048x1080`, `3840x2160`; `duration` = 5 hoặc 10 giây. Với Veo, `video_size` quyết định **cả** tỉ lệ khung (9:16 / 16:9) **và** resolution (720p / 1080p / 4k).

---

## AI providers

Danh sách model là nguồn duy nhất trong tầng service (`LLM_MODELS`, `IMAGE_MODELS`, `VIDEO_MODELS`), frontend lấy qua `GET /settings/models`.

| Loại | Provider | Model | Lấy key |
|---|---|---|---|
| **LLM** (kịch bản) | `gemini` | gemini-2.0-flash, gemini-2.5-pro, gemini-1.5-pro | [aistudio.google.com](https://aistudio.google.com) |
| | `openai` | gpt-4o, gpt-4o-mini, gpt-3.5-turbo | [platform.openai.com](https://platform.openai.com) |
| | `claude` | claude-opus-4-5, claude-sonnet-4-5, claude-haiku-3-5 | [console.anthropic.com](https://console.anthropic.com) |
| | `minimax` | abab6.5s-chat, abab7-chat | [minimax.io](https://api.minimax.io) |
| | `glm` | glm-5.x, glm-4.x, glm-z1-*, glm-4v-* | [z.ai](https://z.ai) |
| **Image** | `gemini` | imagen-3, imagen-2 | aistudio.google.com |
| | `openai` | dall-e-3, dall-e-2 | platform.openai.com |
| | `minimax` | image-01, image-01-live | minimax.io |
| | `glm` | glm-image, cogview-4-250304 | z.ai |
| **Video** | `gemini` (Veo) | veo-3.1-generate-preview, veo-3.1-fast, veo-3.1-lite, veo-3.0-generate-001, gemini-omni-flash-preview | aistudio.google.com |
| | `kling` | kling-v2-master, kling-v1.6-standard, kling-v1-5 | [klingai.com](https://klingai.com) |
| | `runway` | gen3a_turbo, gen3a | [dev.runwayml.com](https://dev.runwayml.com) |
| | `glm` | cogvideox-3 | z.ai |

Với provider `gemini` ở mục Video: nếu chưa cắm key riêng cho Video AI, hệ thống tự fallback sang key của Image AI (cùng Gemini API key).

> **Gọi AI tốn tiền thật.** Veo 3.1 Standard ~$0.40/giây video, Fast ~$0.10/giây, Lite ~$0.05/giây (720p). Một tập 60 giây chia ~12 cảnh × 5s = 60s video.

---

## Cài đặt & chạy

### Cách 1 — Docker Compose (khuyến nghị cho server)

```bash
cd series-drama-studio
cp .env.example .env

# Sinh 2 key bắt buộc
python -c "import secrets; print(secrets.token_urlsafe(48))"                      # → SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # → ENCRYPTION_KEY

# Sửa .env: DB_PASSWORD, SECRET_KEY, ENCRYPTION_KEY
docker compose up -d --build
```

- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

Trước khi dùng compose, xem [Lưu ý & hạn chế đã biết](#lưu-ý--hạn-chế-đã-biết) — cần sửa driver DB và thêm `ffmpeg` vào image backend.

Cập nhật:

```bash
git pull && docker compose up -d --build
```

### Cách 2 — Dev local (Windows / macOS)

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows;  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Sửa .env: DATABASE_URL trỏ tới Postgres local, điền SECRET_KEY + ENCRYPTION_KEY

python run.py                    # http://localhost:8000
```

> **Trên Windows bắt buộc chạy bằng `python run.py`, không dùng `uvicorn app.main:app` trực tiếp.**
> `psycopg` async cần `SelectorEventLoop`; `run.py` set loop này trước khi uvicorn khởi động. Hệ quả kèm theo: `SelectorEventLoop` không hỗ trợ subprocess async, nên `video_service.concat_videos` gọi ffmpeg bằng subprocess đồng bộ trong thread.

**Frontend**

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Frontend đọc `VITE_API_URL` (mặc định `http://localhost:8000`).

**ffmpeg** — cần cho tính năng ghép tập. Kiểm tra: `ffmpeg -version`. Windows: `winget install ffmpeg` hoặc tải từ [ffmpeg.org](https://ffmpeg.org) rồi thêm vào PATH. macOS: `brew install ffmpeg`.

### Tài khoản test

```bash
cd backend
python seed.py
```

Tạo user `test@drama.com` / mật khẩu `123456`. Script idempotent — nếu user đã tồn tại thì chỉ in ID và thoát.

---

## Biến môi trường

Backend đọc `backend/.env` (dev) hoặc environment của container (Docker).

| Biến | Bắt buộc | Mặc định | Ghi chú |
|---|---|---|---|
| `DATABASE_URL` | — | `postgresql+psycopg://postgres:changeme@localhost:5432/drama_studio` | Driver phải là `psycopg` (psycopg3), **không** phải `asyncpg` |
| `SECRET_KEY` | ✅ | — | Ký JWT, tối thiểu 32 ký tự. App **không khởi động** nếu thiếu/quá ngắn |
| `ALGORITHM` | — | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | `10080` (7 ngày) | |
| `ENCRYPTION_KEY` | ✅ | — | Fernet key base64 url-safe 44 ký tự. App **không khởi động** nếu sai định dạng |
| `CORS_ORIGINS` | — | `http://localhost:5173,http://localhost:3000` | Danh sách origin cách nhau bằng dấu phẩy. Không dùng `*` (đi kèm `allow_credentials=True` sẽ mở API cho mọi website) |
| `DATA_DIR` | — | `../data` | Nơi lưu upload/ảnh/video |
| `MAX_UPLOAD_SIZE_MB` | — | `50` | |

Compose bổ sung `DB_PASSWORD` cho container Postgres.

**Không commit `.env`** — đã có trong `.gitignore` cùng `data/`, `outputs/` và file media.

---

## Migration & script tiện ích

Schema được `create_all` tự tạo cho DB mới. Với DB đã có dữ liệu, các cột/bảng thêm sau được migrate bằng script thủ công (chạy 1 lần, từ thư mục `backend/`, idempotent):

| Script | Thay đổi |
|---|---|
| `migrate_add_episodes.py` | Thêm bảng `episodes`, chuyển FK của `scripts`/`images` |
| `migrate_script_versions.py` | Thêm `version`, `is_active`, `parent_id` vào `scripts` |
| `migrate_scene_image_ids.py` | Thêm `image_ids`, `extra_prompt` vào `scenes` |
| `migrate_scene_extra_prompt.py` | Thêm `extra_prompt` vào `scenes` |
| `migrate_video_started_at.py` | Thêm `started_at` vào `videos` + reset task `running` mồ côi |
| `migrate_merged_video.py` | Thêm `merged_video_path/_status/_error` vào `episodes` |
| `check_schema.py` | In schema thực tế trong DB để đối chiếu |

Script kiểm thử tay: `test_system.py` (smoke test toàn hệ thống), `test_veo3.py` (gen video Veo), `test_glm_flow.py` (luồng GLM).

---

## API endpoints

Xác thực: `Authorization: Bearer <token>` cho mọi route ngoài `/auth/register`, `/auth/login`, `/health`. Swagger đầy đủ tại `/docs`.

**Auth** — `POST /auth/register` · `POST /auth/login` · `GET /auth/me`

**Projects** — `GET|POST /projects` · `GET|PATCH|DELETE /projects/{project_id}`

**Episodes** — `GET|POST /projects/{pid}/episodes` · `GET|PATCH|DELETE /projects/{pid}/episodes/{eid}`

**Documents** — `POST|GET /projects/{pid}/documents` · `DELETE /projects/{pid}/documents/{doc_id}`

**Scripts & Scenes**

| Method | Path | Mô tả |
|---|---|---|
| POST | `/projects/{pid}/episodes/{eid}/scripts/generate` | Gọi LLM, trả `{ content, scenes[] }` (chưa lưu DB) |
| POST | `/projects/{pid}/episodes/{eid}/scripts/save` | Lưu thành version mới + ghi Scene |
| GET | `/projects/{pid}/episodes/{eid}/scripts` | Danh sách version kèm scene |
| PATCH | `/projects/{pid}/scenes/{scene_id}` | Sửa 1 cảnh (ảnh, prompt, thoại, thời lượng…) |
| PATCH | `/projects/{pid}/episodes/{eid}/scripts/{sid}/activate` | Đặt version active |
| POST | `/projects/{pid}/episodes/{eid}/scripts/{sid}/reparse-scenes` | Nhờ LLM bóc lại scene list (preview) |
| POST | `.../reparse-scenes/confirm` | Xác nhận ghi đè scene list |

**Images** — `POST /projects/{pid}/images/generate` · `POST /projects/{pid}/images/save` · `GET /projects/{pid}/images` (lọc theo `episode_id`/`type`) · `PATCH|DELETE /projects/{pid}/images/{image_id}`

**Videos**

| Method | Path | Mô tả |
|---|---|---|
| POST | `/projects/{pid}/videos/generate` | `202` — nhận `scene_ids[]`, `video_size`, `duration`; chạy ngầm |
| GET | `/projects/{pid}/videos` | Danh sách video (lọc theo scene/episode) |
| GET | `/projects/{pid}/videos/{video_id}` | Trạng thái 1 video |
| DELETE | `/projects/{pid}/videos/{video_id}` | Xoá bản ghi + file |
| GET | `/projects/{pid}/videos/{video_id}/download` | Tải video 1 cảnh |
| POST | `/projects/{pid}/episodes/{eid}/videos/merge` | `202` — ghép nháp cả tập bằng ffmpeg |
| GET | `/projects/{pid}/episodes/{eid}/videos/merge` | Trạng thái ghép |
| GET | `/projects/{pid}/episodes/{eid}/videos/download` | Tải bản ghép |

**Settings** — `GET|PUT /settings/api-keys` · `POST /settings/api-keys/test` · `GET /settings/models` · `POST /settings/test-gemini-raw` (debug Gemini raw response)

**Khác** — `GET /health` · `GET /data/{...}` (static: ảnh, video, thumbnail)

---

## Lưu ý & hạn chế đã biết

1. **`docker-compose.yml` đang set `DATABASE_URL` với driver `asyncpg`, nhưng `requirements.txt` chỉ cài `psycopg[binary]`** → container backend không kết nối được DB. Sửa thành `postgresql+psycopg://...` trong compose (hoặc thêm `asyncpg` vào requirements) trước khi chạy Docker.
2. **`backend/Dockerfile` chưa cài `ffmpeg`** → tính năng ghép tập báo lỗi "FFmpeg không tìm thấy" khi chạy trong Docker. Thêm `ffmpeg` vào lệnh `apt-get install`.
3. **Mỗi scene chỉ giữ 2 video mới nhất** — bản cũ hơn bị xoá tự động khỏi DB và đĩa, kể cả lúc backend khởi động. Cần giữ lâu hơn thì tải về trước.
4. **Không có migration framework** (Alembic) — thay đổi schema phải viết script `migrate_*.py` thủ công.
5. **Chưa có test tự động** — chỉ có script kiểm thử tay (`test_system.py`, `test_veo3.py`, `test_glm_flow.py`).
6. **Token JWT lưu ở cookie non-HttpOnly** (`ds_token`, `SameSite=Strict`) để axios đọc được → chấp nhận được cho môi trường chạy nội bộ LAN, cần xem lại nếu mở ra Internet.
7. **`create_all` không sửa bảng đã tồn tại** — thêm cột mới vào `models.py` vẫn phải viết migration tương ứng.

---

## Tài liệu liên quan

| File | Nội dung |
|---|---|
| `docs/design-process.md` | Quy trình thiết kế UI/UX |
| `docs/episode-template.md` | Mẫu cấu trúc một tập |
| `docs/specs/co-vua-10-tap-spec.md` | Spec series mẫu "Cờ Vua" 10 tập |
| `docs/plans/` | Kế hoạch triển khai theo phase (episode layer, script editor) |
| `../inputs/BRIEF-SERIES-DRAMA-APP-SHORT.md` | Brief gốc của dự án |
