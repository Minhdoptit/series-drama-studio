# Template Cấu Trúc Kịch Bản — 1 Tập Series Drama Hoạt Hình

> **Mục đích:** File này định nghĩa cấu trúc bắt buộc của mỗi tập.
> Khi gen kịch bản bằng AI, prompt phải yêu cầu output theo đúng format này.

---

## PHẦN A — METADATA TẬP

```
TÊN TẬP: [Số tập]: [Tên gợi cảm xúc / action / xung đột]
  VD: TẬP 3: NƯỚC CỜ ĐẦU TIÊN

PHA KỊCH TÍNH: [Một trong các pha sau]
  - KHỞI     : Thiết lập thế giới + nhân vật + biến cố khởi phát (T1)
  - LEO      : Thắng nhỏ, tiến lên — nhân vật tăng trưởng (T2, T3)
  - ĐỔI GIÓ : Nhịp nghỉ, twist, gieo hạt mầm phụ tuyến (T4)
  - BÃO      : Xung đột leo thang, kẻ phản diện ra đòn (T5, T6)
  - ĐÁY      : Nhân vật chính ở điểm thấp nhất (T7)
  - LẬT KÈO : Phản công, chứng minh, thu hoạch arc phụ (T8)
  - ĐỈNH     : Cao trào + gặt cảm xúc sâu (T9 chuẩn bị, T10 finale)

TRẢ HOOK TẬP TRƯỚC: [Hành động đầu tập phải giải quyết hook kết tập trước]
  VD: "Hươu đang ngồi vào ván đấu với Voi (trả hook tò mò T2)"
  [Nếu T1: Không có]

TEXT MỞ ĐẦU (0–3s): "[Câu ngắn, tối đa 5 từ, xuất hiện trên màn hình]"
  VD: "Đừng tốn thời gian nữa" / "Hạng chót bảng đầu"

BRAND MOMENT: [Mức độ và cách tích hợp thương hiệu]
  - Không   : Tập này thuần drama, không cần brand
  - Nhẹ     : Cốc sữa/hộp sữa xuất hiện trong khung, không thoại
  - Trực C  : Mẹ trao sữa + câu thoại ngắn liên quan chăm sóc
  - Mạnh    : Đỉnh cảm xúc brand — ôm/trao + câu thoại chủ đề

THỜI LƯỢNG MỤC TIÊU: [Tổng số giây, thường 45–55s]
```

---

## PHẦN B — HỆ THỐNG NHÂN VẬT TẬP NÀY

> Liệt kê chỉ những nhân vật **XUẤT HIỆN** trong tập này.
> Copy từ Character System chung của series, không thay đổi mô tả.

```
NHÂN VẬT XUẤT HIỆN:
- [Tên nhân vật 1] — [Vai trò trong tập này: chính / phụ / xuất hiện ngắn]
- [Tên nhân vật 2] — ...

NÉT RIÊNG CẦN THỂ HIỆN:
- Bé Hươu: Gõ 2 cái quân tốt khi hồi hộp [chỉ đến T9]
           Gõ 1 cái dứt khoát ở T10 (hết do dự — dùng DUY NHẤT ở T10)
- [Nhân vật khác: nét riêng nếu có]
```

---

## PHẦN C — BẢNG CẢNH (Scene Breakdown)

> **Số cảnh khuyến nghị:** 14–18 cảnh cho 45–55 giây
> **Mỗi cảnh = 2–5 giây**

| NO. | BỐI CẢNH | TÌNH TIẾT | Giây | VOICE OVER |
|-----|----------|-----------|------|------------|
| 1 | [Địa điểm, thời gian] | [LOẠI SHOT]. [TEXT 0-3s nếu là cảnh 1] [Hành động] | s | [Thoại / SFX / nhạc / —] |
| 2 | [— tiếp / địa điểm mới] | [LOẠI SHOT]. [Hành động. Chuyển cảnh nếu có] | s | ... |
| ... | | | | |
| N | | | | |
| | | **TỔNG THỜI LƯỢNG** | **XXs** | |

### Quy tắc loại shot:
| Loại shot | Khi nào dùng |
|---|---|
| `ESTABLISH` | Mở đầu cảnh mới — giới thiệu bối cảnh |
| `ESTABLISH-ACTION` | Mở đầu + ngay lập tức có hành động |
| `ESTABLISH-INSERT` | Mở đầu + zoom vào chi tiết quan trọng |
| `WIDE` | Phản ứng đám đông, quan hệ không gian |
| `MEDIUM` | Tương tác 2+ nhân vật, đối thoại |
| `CLOSE` | Cảm xúc mặt, tay, chi tiết nhỏ |
| `CLOSE-POV` | Điểm nhìn nhân vật chính (chủ quan) |
| `INSERT` | Chi tiết vật thể: quân cờ, sổ, bảng, sữa |
| `TILT UP/DOWN` | Nhấn mạnh kích thước / thứ bậc |
| `CAMERA LIA` | Theo dõi hành động, reveal không gian |

### Quy tắc chuyển cảnh:
| Chuyển cảnh | Ý nghĩa |
|---|---|
| `(chuyển — dissolve)` | Nhảy thời gian, thay đổi không khí |
| `(chuyển — match cut)` | Nối hai hành động tương đồng (quân cờ → quân cờ) |
| `(chuyển — cắt theo ánh nhìn)` | Follow POV nhân vật |
| `(chuyển — camera theo bước)` | Nhân vật di chuyển, camera đi cùng |
| `— tiếp` | Cùng bối cảnh, nối liền cảnh trước |

---

## PHẦN D — HOOK CUỐI TẬP

```
🎣 HOOK CUỐI: [LOẠI HOOK] — [Mô tả hành động/câu thoại cụ thể]

LOẠI HOOK:
  - LỜI HỨA     : Nhân vật cam kết điều gì đó (T1)
  - TÒ MÒ       : Tình huống chưa giải quyết, câu hỏi lơ lửng (T2, T6)
  - ĐE DỌA      : Kẻ phản diện ra đòn hoặc áp lực tăng lên (T3, T5)
  - CẢM XÚC     : Câu nói chạm cảm xúc, cắt đúng lúc (T4)
  - ĐE DỌA MẠNH : Leo thang đe dọa, quyết định sinh tử (T7, T8, T9)
  - KHÔNG HOOK  : Chỉ dùng cho finale T10 — kết thúc thỏa mãn + gợi mở nhẹ

VÍ DỤ:
  🎣 HOOK CUỐI: LỜI HỨA — Hươu trước poster giải, siết quân tốt:
     "Ba tháng nữa... con sẽ có tên trên bảng đó."

  🎣 HOOK CUỐI: ĐE DỌA MẠNH — Gấu mẹ hét loại Hươu;
     Hươu: "Tôi cần bằng chứng." — cắt.
```

---

## PHẦN E — CHECKLIST TRƯỚC KHI GEN

Trước khi prompt AI gen kịch bản tập, đảm bảo đã cung cấp:

- [ ] **Metadata tập:** Tên, pha, trả hook, text mở đầu, brand moment, thời lượng
- [ ] **Character System:** Danh sách nhân vật + đặc điểm series (copy từ spec tổng)
- [ ] **Hook tập trước cần trả:** Câu thoại / hành động cụ thể
- [ ] **Hook tập này muốn kết bằng:** Loại hook + nội dung gợi ý
- [ ] **Brand moment cụ thể:** Nếu có — xuất hiện ở cảnh nào, thoại gì
- [ ] **Gieo/Gặt arc phụ:** Nếu tập này có GIEO hoặc GẶT (VD: T4 GIEO 1 — Gấu tự phụ)
- [ ] **Nét riêng nhân vật phải thể hiện:** VD: gõ quân tốt đúng số lần

---

## PHẦN F — PROMPT MẪU CHO AI GEN KỊCH BẢN

```
Bạn là biên kịch series hoạt hình chuyên nghiệp.
Hãy viết kịch bản chi tiết cho [TẬP X: TÊN TẬP] theo cấu trúc sau:

THÔNG TIN TẬP:
- Pha kịch tính: [...]
- Trả hook tập trước: [...]
- Text mở đầu (0-3s): "[...]"
- Brand moment: [...]
- Thời lượng mục tiêu: [X]s

HỆ THỐNG NHÂN VẬT:
[Paste character system]

YÊU CẦU NỘI DUNG:
- Nội dung chính tập này: [Mô tả tình tiết muốn xảy ra]
- Hook cuối phải là: [LOẠI] — [Gợi ý nội dung]
- Nét riêng bắt buộc: [VD: Hươu gõ 2 cái quân tốt khi hồi hộp]

OUTPUT PHẢI THEO FORMAT:

| NO. | BỐI CẢNH | TÌNH TIẾT | Giây | VOICE OVER |
|-----|----------|-----------|------|------------|
[14–18 hàng]

TỔNG THỜI LƯỢNG: Xs

🎣 HOOK CUỐI: [LOẠI] — [Câu cụ thể]

Lưu ý:
- Mỗi cảnh 2–5 giây, tổng 45–55 giây
- Thoại ngắn, đúng nhân vật
- Cảnh 1 phải có TEXT 0-3s + trả hook tập trước
- Brand moment đặt đúng vị trí đã chỉ định
```

---

## PHẦN G — ARC TỔNG THỂ ĐỂ THAM CHIẾU

> Dùng khi gen từng tập để đảm bảo continuity

```
T1  KHỞI     → Gấu bắt nạt → Mẹ động viên → Lời hứa 3 tháng
T2  LEO      → Có tên bảng → Vào nhánh gặp Gấu cuối → Tò mò
T3  LEO      → Thắng Voi → Cái giá: Gấu chặn đường → Đe dọa
T4  ĐỔI GIÓ → Dạy Chó Con → GIEO 1 (Gấu được chiều) → Cảm xúc
T5  BÃO      → Vào tứ kết → Bị vu gian lận → Đe dọa
T6  BÃO MẠNH → Bị quay lưng → GIEO 2 (Gấu mẹ lộ điểm yếu) → Tò mò
T7  ĐÁY      → Bị xét cáo buộc → Đứng một mình → Đe dọa mạnh
T8  LẬT KÈO  → Chứng minh → GẶT 1 (Gấu thấy mình thiếu gì) → Đe dọa mạnh
T9  ĐỈNH CBỊ → Luyện thế cờ hiểm → Mẹ thầm lặng → Đe dọa mạnh
T10 ĐỈNH     → Chiếu tướng → GẶT sâu (Gấu tự đối mặt) → Gợi mở nhẹ
```
