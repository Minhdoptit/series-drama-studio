# Brainstorm — App 3 Màn Gen Phim

> ✅ **Status: LOCKED** — Tất cả quyết định đã được xác nhận, sẵn sàng build.

## Yêu cầu đã xác nhận

| Màn | Input | Output |
|---|---|---|
| **① Script Studio** | Mô tả đề tài, nhân vật, nội dung | Kịch bản hoàn chỉnh + danh sách cảnh chia sẵn |
| **② Image Studio** | Lời mô tả hoặc upload ảnh mẫu | Ảnh nhân vật / bối cảnh lưu vào project |
| **③ Video Studio** | Chọn cảnh từ kịch bản + chọn ảnh từ thư viện + thêm prompt | Video từng cảnh |

**Navigation:** Sidebar menu → 3 trang riêng  
**Data:** Lưu theo Project, mỗi user có account riêng, không thấy dữ liệu của nhau  
**Deploy:** Server (VPS), nhiều người dùng đồng thời  
**Auth:** Mỗi user đăng nhập bằng email + password  
**API Keys:** Mỗi user tự cắm key AI của mình vào Settings

---

## Luồng UX tổng thể

```
[Projects Dashboard]
        │
        ▼
  Chọn / Tạo Project
        │
   ┌────┴────────────────┐
   │                     │
   ▼                     ▼
① Script Studio     ② Image Studio
   │                     │
   │  (kịch bản + cảnh)  │  (thư viện ảnh)
   └────────┬────────────┘
            │
            ▼
      ③ Video Studio
   [Ghép: Cảnh ↔ Ảnh + Prompt → Gen video]
            │
            ▼
      Kho video → Xem / Tải
```

---

## Màn ① — Script Studio

### Layout đề xuất (2 cột)
```
┌──────────────────────────────────────────────────┐
│  [Project: Cờ Vua - Tập 1]              [⚙ API]  │
├─────────────────────┬────────────────────────────┤
│  PROMPT INPUT       │  OUTPUT                    │
│                     │                            │
│  Phong cách phim:   │  📄 Kịch bản hoàn chỉnh   │
│  [___________]      │  ─────────────────────     │
│                     │  Tập 1: Hạng Tép Riu       │
│  Nhân vật:          │                            │
│  [+ thêm nhân vật]  │  📋 Danh sách cảnh         │
│  • Hươu (10t)       │  ─────────────────────     │
│  • Gấu (10t)        │  C1 | Sảnh đăng ký | 2s   │
│                     │  C2 | — tiếp       | 2s   │
│  Nội dung tập:      │  C3 | — tiếp       | 2s   │
│  [textarea dài]     │  ...                       │
│                     │                            │
│  Thời lượng: [45s]  │  [✓ Lưu vào Project]      │
│                     │                            │
│  [🤖 Gen Kịch bản]  │                            │
└─────────────────────┴────────────────────────────┘
```

---

## Màn ② — Image Studio

### Layout đề xuất
```
┌──────────────────────────────────────────────────┐
│  [Project: Cờ Vua]  [📁 Thư viện ảnh: 12 ảnh]   │
├─────────────────────┬────────────────────────────┤
│  PROMPT INPUT       │  KẾT QUẢ GEN               │
│                     │                            │
│  Loại ảnh:          │  [🖼][🖼][🖼]  ← 3 phương án│
│  ○ Nhân vật         │                            │
│  ○ Bối cảnh         │  [🖼][🖼][🖼]               │
│  ○ Đạo cụ           │                            │
│                     │  Nhấn ảnh → xem to         │
│  Mô tả:             │  [✓ Lưu ảnh này]           │
│  [textarea]         │  [🔄 Gen lại]              │
│                     │                            │
│  Upload ảnh mẫu:    │  ─── Đã lưu vào dự án ─── │
│  [📎 Drag & Drop]   │  [🖼 Hươu] [🖼 Gấu]        │
│                     │  [🖼 Sảnh] [🖼 Nhà]        │
│  Phong cách:        │                            │
│  [3D Pixar mềm ▾]   │                            │
│                     │                            │
│  [🤖 Gen 3 ảnh]     │                            │
└─────────────────────┴────────────────────────────┘
```

---

## Màn ③ — Video Studio

### Layout đề xuất (quan trọng nhất)
```
┌──────────────────────────────────────────────────┐
│  [Project: Cờ Vua]   Tập: [Tập 1 ▾]             │
├──────────────────────────────────────────────────┤
│                                                  │
│  DANH SÁCH CẢNH (từ Script Studio)               │
│  ┌─────────────────────────────────────────────┐ │
│  │ C1 │ Sảnh đăng ký │ 2s │ [🖼 Chọn ảnh] [✓] │ │
│  │    │ ESTABLISH-ACTION. Cận tay Hươu...      │ │
│  │    │ Prompt thêm: [___________________]     │ │
│  ├────────────────────────────────────────────-┤ │
│  │ C2 │ — tiếp       │ 2s │ [🖼 Chọn ảnh] [✓] │ │
│  │    │ WIDE. Gấu con bước chắn ngang...       │ │
│  │    │ Prompt thêm: [___________________]     │ │
│  ├────────────────────────────────────────────-┤ │
│  │ ...                                         │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  [Chọn tất cả] [Bỏ chọn]  Đã chọn: 8/16 cảnh   │
│                                                  │
│  [⚡ Gen video các cảnh đã chọn]  ← confirm modal │
│                                                  │
│  ─── TIẾN TRÌNH ─────────────────────────────── │
│  C1: [████████░░] 80% đang gen...               │
│  C2: [░░░░░░░░░░] chờ...                        │
│  C3: [██████████] ✓ Xong → [▶ Xem] [⬇ Tải]    │
└──────────────────────────────────────────────────┘
```

---

## Kiến trúc dữ liệu (DB Schema đơn giản)

```
Project
  ├── id, name, style, created_at
  │
  ├── Scripts[]
  │     ├── id, content (full text), created_at
  │     └── Scenes[]
  │           ├── scene_no, location, action_desc
  │           ├── shot_type, duration_sec, voice_over
  │           └── image_id (FK → Image, nullable)
  │
  ├── Images[]
  │     ├── id, type (character/bg/prop), label
  │     ├── prompt, file_path, thumbnail_path
  │     └── created_at
  │
  └── Videos[]
        ├── id, scene_id (FK → Scene)
        ├── file_path, status (pending/running/done/error)
        ├── prompt_used, provider (kling/runway/...)
        └── created_at
```

---

## ✅ Stack Final (LOCKED)

| Layer | Quyết định | Lý do |
|---|---|---|
| **Frontend** | React + Vite + TypeScript | Fast dev, type-safe |
| **Styling** | TailwindCSS | Build UI nhanh |
| **Backend** | Python FastAPI (async) | Gọi AI APIs, async I/O |
| **Database** | **PostgreSQL** | Deploy server nhiều user, concurrent writes |
| **ORM** | SQLModel + asyncpg | Async, type-safe |
| **Auth** | **JWT** (email + password) | Mỗi user account riêng |
| **Background** | FastAPI BackgroundTasks | Đủ cho MVP, không cần Redis |
| **File storage** | Local disk → sau đổi S3 | Ảnh, video lưu trên server |
| **Deploy** | **Docker Compose** | 1 lệnh chạy cả app lên VPS |
| **AI Image** | Multi-provider: Gemini / DALL-E | User tự cắm key |
| **AI Video** | Multi-provider: Kling / Runway | User tự cắm key |
| **AI LLM** | Multi-provider: Gemini / GPT-4o | User tự cắm key |

---

## Cấu trúc Docker Compose (deploy)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: drama_studio
      POSTGRES_PASSWORD: changeme
    volumes:
      - ./data/postgres:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db]
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
```

```bash
# Dev local:
docker compose up

# Deploy lên VPS:
git pull && docker compose up -d --build
```

---

## Màn Config (Settings) — mỗi user cắm key riêng

```
⚙️ Cài đặt API  (lưu riêng theo account)

─── LLM (gen kịch bản) ─────────────────────────────
Provider: [Gemini ▾]        Key: [AIza...]  [✓ Test]
Model:    [gemini-2.0-flash ▾]
           ├── gemini-2.0-flash      ← nhanh, rẻ (khuyến nghị)
           ├── gemini-2.5-pro        ← chất lượng cao hơn
           └── gemini-2.0-flash-exp  ← thử nghiệm

─── Image Generation ────────────────────────────────
Provider: [Gemini ▾]        Key: [AIza...]  [✓ Test]
Model:    [imagen-3 ▾]
           ├── imagen-3              ← chất lượng cao nhất
           └── imagen-2              ← nhanh hơn, rẻ hơn

─── Video Generation ────────────────────────────────
Provider: [Kling ▾]         Key: [sk-...]   [✓ Test]
Model:    [kling-v2-master ▾]
           ├── kling-v2-master       ← chất lượng cao
           └── kling-v1.6-standard   ← nhanh hơn, rẻ hơn

[💾 Lưu]  ← key được encrypt trước khi lưu DB
```

---

## Tính năng Đính kèm Tài liệu (Document Context)

User có thể đính kèm file tài liệu để AI đọc thêm khi gen kịch bản hoặc ảnh.

### Luồng xử lý
```
User upload file (PDF / DOCX / TXT / MD)
      ↓
Backend lưu file vào project, extract text
      ↓
Ghép vào prompt gửi lên AI:
  [System prompt]
  [Nội dung tài liệu đính kèm]
  [Prompt của user]
      ↓
AI đọc tài liệu → gen kịch bản / mô tả ảnh
```

### UI trong Script Studio và Image Studio
```
─── Tài liệu tham khảo ──────────────────────
📎 [Kéo thả hoặc chọn file]
   Hỗ trợ: PDF, DOCX, TXT, MD

Đã đính kèm:
  📄 brand-guidelines.pdf      [×]
  📄 character-bible.docx      [×]

⚠️ Tổng ~4,200 tokens / giới hạn 100,000
─────────────────────────────────────────
```

### Kỹ thuật
| Vấn đề | Giải pháp |
|---|---|
| File quá dài, vượt token limit | Cảnh báo + tự cắt, ưu tiên phần đầu |
| PDF có ảnh/bảng | `pdfplumber` extract text thuần |
| DOCX | `python-docx` |
| Gemini API | Hỗ trợ upload file PDF trực tiếp, không cần extract |
| GPT-4o | Cần extract text trước rồi gửi |
| Lưu trữ | Lưu per-project, dùng lại được nhiều lần |



## Schema DB (đã cập nhật đầy đủ)

```
User ──┬── Projects[]
       │     ├── Scripts[] → Scenes[]
       │     ├── Images[]
       │     ├── Videos[]
       │     └── Documents[]        ← tài liệu đính kèm per-project
       │           ├── file_name, file_path, file_type
       │           └── extracted_text, token_count
       └── ApiKeys[]
             ├── llm_provider, llm_model, llm_key (encrypted)
             ├── image_provider, image_model, image_key (encrypted)
             └── video_provider, video_model, video_key (encrypted)
```

Mọi bảng đều có `user_id` → user chỉ thấy data của mình.


---

## Bước tiếp theo

Design đã locked → sẵn sàng chạy `/ck:plan` để tạo implementation plan chi tiết và bắt đầu code.

---

## 🎨 UI Design Guidelines

> **Triết lý:** Giao diện trắng, gọn, chuyên nghiệp — theo phong cách Linear / Notion / Vercel Dashboard. **Không** có dấu hiệu AI-generated design.

---

### Màu sắc (Color System)

```css
/* Nền chính — trắng tuyệt đối */
--bg-base:        #FFFFFF;
--bg-subtle:      #F9FAFB;   /* nền panel, sidebar */
--bg-hover:       #F3F4F6;   /* hover state */

/* Border */
--border:         #E5E7EB;   /* viền nhẹ, không đậm */
--border-strong:  #D1D5DB;

/* Text */
--text-primary:   #111827;   /* tiêu đề, nội dung chính */
--text-secondary: #6B7280;   /* label, placeholder */
--text-muted:     #9CA3AF;

/* Accent — 1 màu chủ đạo duy nhất */
--accent:         #2563EB;   /* xanh dương chuyên nghiệp */
--accent-hover:   #1D4ED8;
--accent-light:   #EFF6FF;   /* background nhạt cho badge/tag */

/* Trạng thái */
--success:        #16A34A;
--warning:        #D97706;
--error:          #DC2626;
```

---

### Typography

```css
/* Font: Inter — chuẩn product design */
font-family: 'Inter', -apple-system, sans-serif;

/* Scale */
--text-xs:   12px / line-height: 16px;
--text-sm:   13px / line-height: 20px;   /* body, label */
--text-base: 14px / line-height: 22px;   /* default */
--text-lg:   16px / line-height: 24px;   /* heading nhỏ */
--text-xl:   20px / line-height: 28px;   /* heading lớn */
--text-2xl:  24px / line-height: 32px;   /* page title */

/* Weight */
Regular (400): body text
Medium  (500): label, nav item
Semibold(600): button, heading
Bold    (700): page title, số liệu quan trọng
```

---

### Spacing & Layout

```
Grid: 8px base unit
  4px  — gap nhỏ (icon ↔ text)
  8px  — padding trong component
  12px — gap giữa elements
  16px — padding trong card, panel
  24px — gap giữa sections
  32px — padding page

Sidebar: 240px fixed
Content: fluid, max-width 1200px
Column gap: 24px
```

---

### Components

**Button**
```
Primary:   bg #2563EB, text white, radius 6px, height 36px, px 14px
Secondary: bg white, border #E5E7EB, text #374151
Ghost:     bg transparent, text #6B7280, hover bg #F3F4F6
Danger:    bg white, border #FECACA, text #DC2626
```

**Input / Textarea**
```
border: 1px solid #E5E7EB
border-radius: 6px
padding: 8px 12px
focus: border #2563EB, ring 2px #BFDBFE (nhạt)
background: #FFFFFF
font-size: 14px
```

**Card**
```
background: #FFFFFF
border: 1px solid #E5E7EB
border-radius: 8px
padding: 16px
shadow: KHÔNG dùng shadow nặng
        → chỉ dùng border để tách biệt
```

**Badge / Tag**
```
background: #EFF6FF (xanh nhạt)
color: #1D4ED8
border-radius: 4px
padding: 2px 8px
font-size: 12px
```

---

### ❌ Những thứ KHÔNG làm (Anti-AI-Design Rules)

| Không làm | Làm thay thế |
|---|---|
| Gradient màu tím/xanh loang | Màu solid đơn giản |
| Glassmorphism (blur nền) | Border + background trắng |
| Shadow nặng (box-shadow lớn) | Chỉ dùng border để phân tách |
| Dark mode mặc định | Light mode trắng làm default |
| Neon / glow effect | Không có glow, không có glow |
| Animation quá nhiều | Chỉ transition 150ms cho hover/focus |
| Icon quá to, decorative | Icon nhỏ 16px, functional only |
| Font chữ cách điệu | Inter thuần, không font display |
| Nhiều màu accent | 1 màu accent duy nhất (#2563EB) |
| Rounded quá tròn (radius > 12px) | radius 6-8px cho component |

---

### Tham khảo Style

Phong cách giao diện hướng tới:
- **Linear** (linear.app) — gọn, tối giản, chuyên nghiệp
- **Vercel Dashboard** — trắng, border rõ, typography sắc
- **Notion** — content-first, không distraction
- **GitHub** — consistent, functional, không thừa

**Không theo:** Dribbble shots, AI-generated mockups, template Figma Community có nhiều gradient.
