# Phase 3 — Testing & Integration

**Status:** Pending  
**Effort:** ~0.5 ngày  
**Blocked by:** Phase 1 + Phase 2

---

## Context

- Backend: FastAPI docs tại `http://localhost:8000/docs`
- Frontend: Vite dev server tại `http://localhost:3000`

---

## Test Scenarios

### Backend API Tests (thủ công qua /docs)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | POST `/scripts/save` với content mới | Script mới `version=2`, `is_active=True`; bản cũ `is_active=False` |
| 2 | GET `/scripts` | Trả `version`, `is_active` trong mỗi item |
| 3 | PATCH `/scripts/{id}/activate` với id bản cũ | is_active đổi, bản mới → False |
| 4 | POST `/scripts/{id}/reparse-scenes` | Trả JSON `{scenes: [...], count: N}` |
| 5 | POST `/scripts/{id}/reparse-scenes/confirm` | Scenes trong DB thay bằng scenes mới |
| 6 | POST `/scripts/save` sau khi chưa chạy migration | Phải trả lỗi DB rõ ràng (không crash server) |

### Frontend Integration Tests

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Vào ScriptStudio khi đã có kịch bản đã lưu | Textarea tự fill content, không trống |
| 2 | Sửa vài từ trong textarea | Badge "chưa lưu" xuất hiện |
| 3 | Nhấn Lưu | Version tăng, dropdown lịch sử hiện thêm entry |
| 4 | Chọn version cũ trong dropdown | Textarea đổi về content version đó |
| 5 | Sau khi lưu → modal "cập nhật cảnh?" → chọn Không | Modal đóng, cảnh không đổi |
| 6 | Sau khi lưu → modal → chọn Có → preview scenes → Xác nhận | Toast success, VideoStudio hiện cảnh mới |

---

## Todo List

- [ ] Chạy migration: `python migrate_script_versions.py`
- [ ] Restart backend, check không có import errors
- [ ] Test API bằng `/docs` — 5 scenarios backend
- [ ] Test frontend flow end-to-end — 6 scenarios
- [ ] Check console không có warnings/errors
- [ ] Verify VideoStudio vẫn hoạt động sau khi scenes update

---

## Success Criteria

- [ ] Tất cả API tests pass
- [ ] Frontend flow end-to-end không lỗi
- [ ] Migration idempotent (chạy 2 lần không crash)
- [ ] Không có regression ở VideoStudio (vẫn load được scenes)
