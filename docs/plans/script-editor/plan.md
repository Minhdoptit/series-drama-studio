---
title: "Script Editor — Sửa kịch bản sau khi gen"
description: "Thêm tính năng chỉnh sửa full text kịch bản với version history và rollback"
status: in-progress
priority: P1
effort: 3d
tags: [feature, frontend, backend, database]
blockedBy: []
blocks: []
created: 2026-07-24
---

# Script Editor — Sửa kịch bản sau khi gen

## Overview

Hiện tại kịch bản sau khi gen chỉ có thể xem và lưu — không sửa được.
Plan này thêm khả năng:
- **Edit full text** kịch bản trong textarea
- **Version history**: mỗi lần lưu = phiên bản mới (không xóa cũ)
- **Rollback**: chọn phiên bản cũ từ dropdown để khôi phục
- **Sync cảnh**: sau khi lưu, hỏi có re-parse scenes không

## Phases

| Phase | Tên | Status |
|-------|-----|--------|
| 1 | [Backend: DB + APIs](./phase-01-backend.md) | ✅ Done |
| 2 | [Frontend: Script Editor UI](./phase-02-frontend.md) | ✅ Done |
| 3 | [Testing & Integration](./phase-03-testing.md) | Pending |

## Dependencies

- `app/models.py` — Script model cần 3 field mới
- `app/api/scripts.py` — 3 API endpoints mới/sửa
- `frontend/src/pages/ScriptStudio.tsx` — UI editor chính
