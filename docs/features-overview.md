# Tính năng — Series Drama Studio

App sản xuất phim hoạt hình ngắn nhiều tập bằng AI, chạy trên trình duyệt, giao diện tiếng Việt.
Toàn bộ chuỗi công việc nằm trong một chỗ: **viết kịch bản → tạo hình → chia cảnh → dựng video từng cảnh → ghép bản nháp**.

Định dạng đầu ra mặc định: mỗi tập 45–60 giây, khung dọc 9:16, phong cách 3D mềm kiểu Pixar.

---

## Bản đồ tính năng

```
                          ┌──────────────────┐
                          │   Cài đặt API    │  provider · model · key
                          └────────┬─────────┘  (LLM · Image · Video)
                                   │ dùng chung cho mọi dự án
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐        ┌────────▼────────┐        ┌────────▼────────┐
│  Dự án (series)│───────▶│    Tập phim     │        │ Nhân vật chung  │
│  tên · phong   │  1:N   │  ep_no · tên    │        │ dùng lại mọi tập│
│  cách chung    │        └────────┬────────┘        └────────┬────────┘
└────────────────┘                 │                          │
                    ┌──────────────┼──────────────┐           │
                    │              │              │           │
            ┌───────▼──────┐ ┌─────▼──────┐ ┌────▼───────┐   │
            │Studio Kịch   │ │Studio Hình │ │Studio Video│◀──┘
            │Bản           │ │Ảnh (tập)   │ │            │  gán ảnh
            │· tài liệu    │ │· bối cảnh  │ │· gen hàng  │  vào cảnh
            │· gen kịch bản│ │· đạo cụ    │ │  loạt      │
            │· bảng cảnh   │ │            │ │· ghép tập  │
            │· phiên bản   │ │            │ │            │
            └──────────────┘ └────────────┘ └────────────┘
```

| Nhóm | Tính năng chính |
|---|---|
| [Tài khoản](#1-tài-khoản--dữ-liệu-riêng-từng-người) | Đăng ký/đăng nhập, mỗi người một bộ API key, dữ liệu tách biệt |
| [Dự án & tập phim](#2-dự-án--tập-phim) | Nhiều series, nhiều tập, đánh số tập tự động, badge tiến độ |
| [Kịch bản](#3-studio-kịch-bản) | Upload tài liệu, gen bằng AI, sửa tay, lịch sử phiên bản, bảng cảnh |
| [Hình ảnh](#4-studio-hình-ảnh) | Gen 3 phương án/lần, 3 loại ảnh, thư viện chung series + thư viện riêng tập |
| [Video](#5-studio-video) | Gán nhiều ảnh vào một cảnh, gen hàng loạt chạy ngầm, theo dõi tiến độ |
| [Ghép tập](#6-ghép-bản-nháp-cả-tập) | Nối các cảnh thành một file, xem trước, tải về |
| [Cài đặt AI](#7-cài-đặt-ai) | 5 nhà cung cấp LLM, 4 nhà cung cấp ảnh, 4 nhà cung cấp video |
| [Nền tảng](#8-tính-năng-nền) | Chạy ngầm, chống mất dữ liệu, mã hoá key, tự dọn rác |

---

## 1. Tài khoản & dữ liệu riêng từng người

- **Đăng ký bằng email + mật khẩu + họ tên**, đăng nhập luôn ngay sau khi đăng ký.
- **Ghi nhớ đăng nhập 7 ngày** — đóng trình duyệt hay F5 đều không bị bật ra ngoài; hết hạn thì tự chuyển về trang đăng nhập.
- **Mỗi người một bộ API key riêng** — không dùng chung, không thấy key của nhau.
- **Dữ liệu tách biệt hoàn toàn**: dự án, tập, cảnh, ảnh, video của ai người đó thấy. Kể cả biết ID của người khác cũng không mở được.
- **Đăng xuất** ngay ở góc dưới thanh bên, hiện tên và email đang đăng nhập.
- **Thanh điều hướng đổi theo ngữ cảnh** — đang ở dự án nào, tập nào thì hiện đúng các mục của cấp đó.

## 2. Dự án & tập phim

**Dự án = một series phim.**

- Danh sách dạng thẻ: tên, phong cách hình ảnh, mô tả, ngày cập nhật.
- Tạo dự án chỉ cần đặt tên — ô phong cách điền sẵn *"3D Pixar mềm, nhân vật con vật cách điệu dáng người"*, sửa được. Phong cách này áp cho toàn series.
- Xoá dự án có xác nhận, và xoá sạch mọi thứ bên trong kèm file trên đĩa.

**Tập phim nằm trong dự án.**

- **Số tập tự tăng** — không phải tự đánh số.
- Thẻ mỗi tập hiện badge **"Có kịch bản" / "Chưa có kịch bản"** để biết ngay tập nào đang dở.
- Mỗi thẻ có **3 nút tắt**: Kịch bản · Hình ảnh · Video.
- Thêm tập nhanh: gõ tên rồi Enter.
- Trong dự án có 2 tab: **Các tập phim** (kèm số lượng) và **Nhân vật chung**.

## 3. Studio Kịch Bản

### Nhập thông tin

- **Danh sách nhân vật động** — mỗi dòng tên / tuổi / mô tả ngắn, thêm và xoá tự do.
- **Nội dung tập** — mô tả tình tiết, cảm xúc muốn truyền tải.
- **Thời lượng mục tiêu** chọn bằng thanh trượt 20–180 giây.
- **Phong cách hình ảnh** riêng cho tập (kế thừa ý tưởng chung của series).

### Tài liệu tham khảo

- **Kéo–thả nhiều file cùng lúc**: PDF, DOCX, TXT, MD.
- App **bóc chữ ngay khi tải lên** và hiện **số token ước lượng** của từng file.
- **Tick chọn** tài liệu nào cần đưa cho AI đọc — không phải lúc nào cũng dùng hết.
- **Cảnh báo đỏ khi tổng vượt 100.000 token** ("AI sẽ chỉ đọc phần đầu").
- Xoá tài liệu khỏi danh sách bất cứ lúc nào.

### Gen & chỉnh sửa

- Bấm một nút, AI trả về **kịch bản đầy đủ + bảng danh sách cảnh**, kèm thông báo bóc được bao nhiêu cảnh.
- Chưa cắm API key thì thông báo lỗi có **link bấm được sang thẳng trang Cài đặt**.
- Kịch bản **sửa trực tiếp** trong ô soạn thảo. Có thay đổi chưa lưu thì hiện nhãn **"✏️ chưa lưu"**; nút Lưu chỉ xuất hiện khi thực sự có gì để lưu.

### Lịch sử phiên bản

- **Mỗi lần lưu là một phiên bản** (v1, v2, v3…) — không bản nào bị mất.
- Dropdown **Lịch sử** liệt kê tất cả kèm thời gian tạo, bản đang dùng có nhãn `● active`.
- **Bấm vào bản cũ để khôi phục** — quay lại bất kỳ phiên bản nào.

### Đồng bộ danh sách cảnh

Sau khi lưu, app hỏi có cập nhật bảng cảnh theo nội dung mới không:

- Chọn **Không** → giữ nguyên cảnh cũ và ảnh đã gán.
- Chọn **Cập nhật** → AI đọc lại kịch bản, **hiện preview** danh sách cảnh mới (số cảnh, địa điểm, thời lượng) để duyệt. Chỉ khi bấm xác nhận mới ghi đè.

### Bảng cảnh

- Mỗi dòng: **số cảnh · địa điểm · cỡ/góc máy · thời lượng**.
- Bấm để mở rộng xem **mô tả hành động** và **lời thoại (🎙)**.

## 4. Studio Hình Ảnh

Hai thư viện riêng biệt, dùng chung một giao diện:

| | **Nhân vật chung** | **Hình ảnh tập** |
|---|---|---|
| Dùng cho | Nhân vật xuất hiện xuyên suốt series | Bối cảnh, đạo cụ riêng của tập |
| Phạm vi | Mọi tập đều chọn được | Chỉ tập đó |

**Tạo ảnh:**

- **3 loại ảnh**: Nhân vật · Bối cảnh · Đạo cụ, mỗi loại có badge riêng trong thư viện.
- **5 phong cách dựng sẵn**: 3D Pixar mềm · Anime Ghibli · 2D cartoon · Watercolor · Semi-realistic 3D.
- **Gen 3 phương án mỗi lần** để so sánh, chưa ưng thì bấm *Gen lại*, ưng cái nào lưu cái đó.
- **Bắt buộc đặt tên ảnh** trước khi lưu — tên này hiện trong bảng chọn ảnh lúc ghép cảnh, và được đưa thẳng vào mô tả gửi AI dựng video.

**Thư viện:**

- Lưới thumbnail, badge loại ảnh ở góc.
- **Đổi tên tại chỗ** — bấm vào tên, Enter để lưu, Escape để huỷ.
- Xoá ảnh không cần rời trang.
- Chuyển sang tập khác thì thư viện tự tải lại đúng phạm vi tập đó.

> 💡 Nhân vật nhiều trang phục thì tạo nhiều ảnh với tên phân biệt — *"Hươu con đồng phục"*, *"Hươu con áo mưa"* — rồi chọn đúng ảnh cho từng cảnh.

## 5. Studio Video

### Chuẩn bị cảnh

- **Gán nhiều ảnh tham chiếu cho một cảnh** — cửa sổ chọn hiện toàn bộ thư viện dạng lưới khung dọc, tick chọn được cả nhân vật lẫn bối cảnh cho cùng một cảnh.
- Ảnh đã gán hiện **thumbnail nhỏ kèm nhãn ngay tại dòng cảnh**, mỗi ảnh có nút `×` để bỏ riêng lẻ.
- **Prompt phụ cho từng cảnh** — ô nhập ngay dưới mỗi cảnh để bổ sung yêu cầu riêng ("nhân vật cười tươi", "trời mưa nhẹ"). **Tự lưu** sau khi ngừng gõ, không cần bấm nút.
- **Chọn kịch bản** nếu tập có nhiều phiên bản.

### Tuỳ chọn xuất

- **5 preset tỉ lệ + độ phân giải**: `9:16 720p` · `9:16 1080p` · `16:9 720p` · `16:9 4K` · `1:1 720p`. Nhãn ghi rõ độ phân giải vì giá tính theo giây phụ thuộc vào nó.
- **Thời lượng 5 hoặc 10 giây**; dùng Gemini/Veo thì tự khoá ở 8 giây (đúng giới hạn của model).

### Gen hàng loạt

- **Tick từng cảnh** hoặc *Chọn tất cả*, hiện "Đã chọn x/y cảnh".
- **Hộp thoại xác nhận số cảnh** trước khi gọi — vì mỗi lần gọi là tiền thật.
- Chạy ngầm ở máy chủ, không phải ngồi canh trình duyệt.

### Theo dõi tiến độ

- Trạng thái từng cảnh: `⏳ Chờ gen` → `⚡ Đang gen` → xong / lỗi.
- **Đồng hồ đếm giây** và **thanh tiến độ** ước lượng theo mốc trung bình 3 phút/video.
- **Rời trang hoặc F5 thoải mái** — quay lại app tự nhận ra video nào còn chạy và theo dõi tiếp.
- Xong toàn bộ có **thông báo tổng kết** số video hoàn thành.
- Lỗi hiện **lý do bằng tiếng Việt** ngay tại dòng cảnh, rê chuột xem đầy đủ.

### Xem & tải

- Cảnh xong có **trình phát nhúng ngay tại chỗ**.
- Nút tải riêng video của từng cảnh.

## 6. Ghép bản nháp cả tập

- Một nút **Ghép Tập** — nối các cảnh theo thứ tự thành một file duy nhất.
- Xác nhận số video trước khi ghép.
- Chạy ngầm, có theo dõi trạng thái.
- Xong: **trình phát xem trước** + nút **Tải toàn tập**.
- **Kết quả được lưu lại** — mở lại trang vẫn thấy bản ghép lần trước, không phải ghép lại.
- Lỗi hiện bảng đỏ kèm lý do cụ thể.

## 7. Cài đặt AI

- **3 nhóm độc lập**: LLM (viết kịch bản) · Image AI (vẽ ảnh) · Video AI (dựng video). Mỗi nhóm chọn nhà cung cấp, model và key riêng.

| Việc | Nhà cung cấp hỗ trợ |
|---|---|
| Viết kịch bản | Gemini · OpenAI · Claude · MiniMax · GLM (Zhipu) |
| Vẽ ảnh | Gemini (Imagen) · OpenAI (DALL·E) · MiniMax · GLM (CogView) |
| Dựng video | Gemini (Veo 3.x) · Kling · Runway · GLM (CogVideoX) |

- **Danh sách model lấy động từ máy chủ** — không bao giờ chào một model mà app không gọi được.
- Đổi nhà cung cấp thì model tự nhảy về lựa chọn hợp lệ đầu tiên.
- **Nút Kiểm tra** gọi thật lên nhà cung cấp để xác nhận key còn sống, trước khi tốn tiền gen thử.
- **Kiểm tra được key đã lưu** mà không cần nhập lại.
- Key nhập dạng ẩn, có badge **"Key đã lưu"**, để trống nếu không muốn đổi.
- Dùng Gemini/Veo dựng video mà chưa cắm key riêng thì **tự lấy key của Image AI** (cùng một Gemini API key).

> 💰 Chi phí tham khảo (Veo 3.1, 720p): Standard ~$0.40/giây · Fast ~$0.10/giây · Lite ~$0.05/giây. Nên gen thử 1–2 cảnh trước khi chạy cả tập.

## 8. Tính năng nền

| Tính năng | Ý nghĩa với người dùng |
|---|---|
| **Ảnh mẫu được gửi thật sự** | Ảnh đã duyệt được đọc từ đĩa và gửi đúng định dạng từng nhà cung cấp yêu cầu, kèm nhãn nhân vật trong mô tả cảnh — không có chuyện AI báo OK rồi bỏ qua ảnh |
| **Việc lâu chạy ngầm** | Gen video và ghép tập chạy ở máy chủ, đóng trình duyệt vẫn tiếp tục |
| **Chống task treo** | Máy chủ khởi động lại thì các task dở dang được đánh dấu lỗi kèm lý do, không treo mãi ở trạng thái "đang chạy" |
| **Tự dọn ổ cứng** | Mỗi cảnh chỉ giữ 2 video mới nhất, tự xoá cả file lẫn bản ghi |
| **Mã hoá API key** | Key mã hoá trước khi lưu database, không bao giờ hiển thị lại; app từ chối khởi động nếu cấu hình bảo mật không hợp lệ |
| **Kiểm tra quyền mọi nơi** | Không đọc/sửa được dữ liệu của người khác kể cả khi biết ID |
| **Xoá sạch theo tầng** | Xoá dự án hay tập thì mọi dữ liệu con và file trên đĩa đều được dọn, không để lại rác |
| **Lỗi đọc được** | Thông báo tiếng Việt cho người dùng, chi tiết kỹ thuật ghi log ở máy chủ |
| **Xác nhận trước khi tốn tiền** | Mọi thao tác gọi AI hàng loạt đều hỏi lại kèm số lượng |
| **Sao lưu = copy thư mục** | Toàn bộ ảnh, video, tài liệu nằm gọn trong một thư mục dữ liệu |
| **Chạy nội bộ đa nền tảng** | Windows và macOS, nhiều người trong cùng mạng dùng chung một máy chủ |
