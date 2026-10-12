# Phase 2 — Frontend: Script Editor UI

**Status:** Pending  
**Effort:** ~1.5 ngày  
**Blocked by:** Phase 1 (APIs phải ready trước)

---

## Context

- [`ScriptStudio.tsx`](file:///d:/Project/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/series-drama-studio/frontend/src/pages/ScriptStudio.tsx)
- [`index.css`](file:///d:/Project/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/series-drama-studio/frontend/src/index.css)
- [`lib/api.ts`](file:///d:/Project/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/BRIEFTool%20Ho%E1%BA%A1t%20h%C3%ACnh/series-drama-studio/frontend/src/lib/api.ts)

---

## Key Insights

- `ScriptStudio.tsx` hiện tại: 2 cột (input trái, output phải)
- Output panel: chỉ có `<pre>` hiển thị `content` (read-only)
- `handleSave()` gọi `POST /scripts/save` — cần mở rộng để reload version list sau khi save
- Kịch bản đã lưu (`generated`) chỉ là state local — chưa load từ DB khi user quay lại trang
- Design guideline: Linear/Notion style, không gradient, 1 accent màu `#2563EB`

---

## Requirements

### Functional
- Khi trang load: fetch scripts đã lưu của tập hiện tại → hiện script active trong editor
- Textarea editable cho `content` của script
- Badge "chưa lưu" khi content bị thay đổi so với bản gốc
- Dropdown version history (chỉ hiện nếu có ≥2 phiên bản)
- Nút "Lưu kịch bản" → POST save → show modal sync cảnh
- Modal sync cảnh: "Cập nhật cảnh không?" → [Không] / [Có, re-parse]
- Nếu chọn re-parse: gọi API → show preview scenes → confirm
- Rollback: click version trong dropdown → PATCH activate → reload

### Non-Functional
- Textarea resizable, font monospace 13px, line-height 1.7
- Modal có warning nếu có videos sẽ bị mồ côi
- Toast notifications cho mỗi action

---

## Architecture

```
ScriptStudio.tsx (sửa major)
  ├── State mới:
  │   ├── savedScripts: Script[]          ← list từ DB
  │   ├── activeScript: Script | null     ← is_active=true
  │   ├── editContent: string             ← content đang edit
  │   ├── isDirty: boolean                ← editContent !== activeScript.content
  │   ├── showVersions: boolean           ← dropdown toggle
  │   └── showSyncModal: boolean          ← modal sau khi save
  │
  ├── On mount:
  │   └── GET /scripts → set savedScripts, activeScript, editContent
  │
  ├── handleSave():
  │   ├── POST /scripts/save (editContent)
  │   ├── reload savedScripts
  │   └── showSyncModal = true
  │
  ├── handleActivate(scriptId):
  │   ├── PATCH /scripts/{id}/activate
  │   └── reload → set editContent = new activeScript.content
  │
  └── SyncModal:
      ├── [Không] → dismiss
      └── [Có] → POST /reparse-scenes → preview → POST /confirm
```

---

## Related Files

| File | Action | Mô tả |
|------|--------|--------|
| `frontend/src/pages/ScriptStudio.tsx` | MODIFY | Thêm editor, version UI, load logic |
| `frontend/src/index.css` | MODIFY | Style cho editor, sync modal nếu cần |

---

## Implementation Steps

### Step 1 — Thêm interfaces và state mới

```typescript
interface Script {
  id: string
  episode_id: string
  title: string | null
  content: string
  created_at: string
  version: number
  is_active: boolean
  scenes: Scene[]
}

// State mới trong component:
const [savedScripts, setSavedScripts] = useState<Script[]>([])
const [activeScript, setActiveScript] = useState<Script | null>(null)
const [editContent, setEditContent] = useState('')
const [isDirty, setIsDirty] = useState(false)
const [showVersions, setShowVersions] = useState(false)
const [showSyncModal, setShowSyncModal] = useState(false)
const [reparsePreview, setReparsePreview] = useState<Scene[] | null>(null)
const [reparseLoading, setReparseLoading] = useState(false)
```

### Step 2 — Load scripts khi mount

```typescript
const loadSavedScripts = async () => {
  if (!projectId || !epId) return
  try {
    const { data } = await api.get(`/projects/${projectId}/episodes/${epId}/scripts`)
    setSavedScripts(data)
    const active = data.find((s: Script) => s.is_active)
    if (active) {
      setActiveScript(active)
      setEditContent(active.content)
    }
  } catch { /* silent */ }
}

useEffect(() => {
  loadSavedScripts()
}, [projectId, epId])
```

### Step 3 — Track isDirty

```typescript
useEffect(() => {
  setIsDirty(editContent !== (activeScript?.content ?? ''))
}, [editContent, activeScript])
```

### Step 4 — Sửa `handleSave`

```typescript
const handleSave = async () => {
  if (!activeScript && !generated) return
  const contentToSave = activeScript ? editContent : generated!.content
  const titleToSave = activeScript?.title || generated?.title
  const scenesToSave = generated?.scenes // chỉ có khi gen mới, không khi edit

  setSaving(true)
  try {
    await api.post(`/projects/${projectId}/episodes/${epId}/scripts/save`, {
      title: titleToSave,
      content: contentToSave,
      scenes: scenesToSave ?? [],
    })
    await loadSavedScripts()
    setIsDirty(false)
    setShowSyncModal(true)
    toast.success('Đã lưu kịch bản!')
  } catch {
    toast.error('Lưu thất bại')
  } finally {
    setSaving(false)
  }
}
```

### Step 5 — Rollback

```typescript
const handleActivate = async (scriptId: string) => {
  try {
    await api.patch(`/projects/${projectId}/episodes/${epId}/scripts/${scriptId}/activate`)
    await loadSavedScripts()
    setShowVersions(false)
    toast.success('Đã khôi phục phiên bản!')
  } catch {
    toast.error('Khôi phục thất bại')
  }
}
```

### Step 6 — SyncModal: Reparse flow

```typescript
const handleReparse = async () => {
  if (!activeScript) return
  setReparseLoading(true)
  try {
    const { data } = await api.post(
      `/projects/${projectId}/episodes/${epId}/scripts/${activeScript.id}/reparse-scenes`
    )
    setReparsePreview(data.scenes)
  } catch {
    toast.error('Parse cảnh thất bại')
  } finally {
    setReparseLoading(false)
  }
}

const handleConfirmReparse = async () => {
  if (!activeScript || !reparsePreview) return
  try {
    await api.post(
      `/projects/${projectId}/episodes/${epId}/scripts/${activeScript.id}/reparse-scenes/confirm`,
      { scenes: reparsePreview }
    )
    toast.success(`Đã cập nhật ${reparsePreview.length} cảnh!`)
    setShowSyncModal(false)
    setReparsePreview(null)
    await loadSavedScripts()
  } catch {
    toast.error('Cập nhật cảnh thất bại')
  }
}
```

### Step 7 — UI: Output panel khi có kịch bản đã lưu

Khi `activeScript` tồn tại, thay `<pre>` read-only bằng textarea editable:

```tsx
{/* Version history header */}
{savedScripts.length > 1 && (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
        Phiên bản: v{activeScript?.version ?? 1}
      </span>
      {isDirty && (
        <span className="badge" style={{ background: '#FEF3C7', color: '#92400E', fontSize: 11 }}>
          ✏️ chưa lưu
        </span>
      )}
    </div>
    <button
      className="btn btn-ghost btn-sm"
      onClick={() => setShowVersions(!showVersions)}
    >
      <History size={14} /> Lịch sử
    </button>
  </div>
)}

{/* Version dropdown */}
{showVersions && (
  <div className="card" style={{ marginBottom: 8, padding: 8 }}>
    {savedScripts.map(s => (
      <div
        key={s.id}
        onClick={() => handleActivate(s.id)}
        style={{
          padding: '6px 10px',
          cursor: 'pointer',
          borderRadius: 4,
          display: 'flex',
          justifyContent: 'space-between',
          background: s.is_active ? 'var(--accent-light)' : 'transparent',
          color: s.is_active ? 'var(--accent)' : 'var(--text-primary)',
          fontSize: 13,
        }}
      >
        <span>v{s.version} — {new Date(s.created_at).toLocaleString('vi-VN')}</span>
        {s.is_active && <span style={{ fontWeight: 600 }}>● active</span>}
      </div>
    ))}
  </div>
)}

{/* Editable textarea */}
<textarea
  className="textarea"
  style={{ fontFamily: 'monospace', fontSize: 13, lineHeight: 1.7, minHeight: 280, resize: 'vertical' }}
  value={editContent}
  onChange={e => setEditContent(e.target.value)}
/>
```

### Step 8 — SyncModal component (inline hoặc tách file)

```tsx
{showSyncModal && (
  <div className="modal-overlay">
    <div className="modal" style={{ maxWidth: 420 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
        ✅ Đã lưu kịch bản
      </h3>
      {!reparsePreview ? (
        <>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 16 }}>
            Bạn có muốn cập nhật danh sách cảnh từ kịch bản mới không?
          </p>
          <p style={{ fontSize: 12, color: 'var(--warning)', marginBottom: 20 }}>
            ⚠️ Cảnh cũ đã gán ảnh/video sẽ bị reset.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary" onClick={() => setShowSyncModal(false)}>
              Không, giữ cảnh cũ
            </button>
            <button className="btn btn-primary" onClick={handleReparse} disabled={reparseLoading}>
              {reparseLoading ? <span className="spinner" /> : null}
              Cập nhật cảnh
            </button>
          </div>
        </>
      ) : (
        <>
          <p style={{ fontSize: 14, marginBottom: 12 }}>
            Tìm thấy <strong>{reparsePreview.length} cảnh</strong> từ kịch bản mới:
          </p>
          <div style={{ maxHeight: 200, overflowY: 'auto', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 16 }}>
            {reparsePreview.map((s, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                C{s.scene_no} · {s.location} · {s.duration_sec}s
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary" onClick={() => { setShowSyncModal(false); setReparsePreview(null); }}>
              Hủy
            </button>
            <button className="btn btn-primary" onClick={handleConfirmReparse}>
              ✓ Xác nhận cập nhật {reparsePreview.length} cảnh
            </button>
          </div>
        </>
      )}
    </div>
  </div>
)}
```

### Step 9 — Thêm import icon `History` từ lucide-react

```typescript
import { Wand2, Save, ChevronDown, ChevronUp, Plus, X, ChevronRight, History } from 'lucide-react'
```

---

## Todo List

- [ ] Thêm interface `Script` (mới, bao gồm version, is_active)
- [ ] Thêm state: `savedScripts`, `activeScript`, `editContent`, `isDirty`, `showVersions`, `showSyncModal`, `reparsePreview`, `reparseLoading`
- [ ] Thêm `loadSavedScripts()` và gọi trong useEffect
- [ ] Track `isDirty` qua useEffect
- [ ] Sửa `handleSave()` — reload sau khi save, show sync modal
- [ ] Thêm `handleActivate()` — rollback version
- [ ] Thêm `handleReparse()` và `handleConfirmReparse()`
- [ ] UI: version history header + dropdown
- [ ] UI: textarea editable thay vì `<pre>` (khi có activeScript)
- [ ] UI: SyncModal với 2 bước (confirm → preview → apply)
- [ ] Thêm import `History` từ lucide-react
- [ ] Kiểm tra modal styles trong `index.css` (modal-overlay, modal đã có chưa)

---

## Success Criteria

- [ ] Khi vào ScriptStudio, nếu đã có kịch bản → tự động load và hiện trong editor
- [ ] Textarea editable, có thể gõ/sửa tự do
- [ ] Badge "chưa lưu" xuất hiện khi content bị thay đổi
- [ ] Nút Lưu → tạo phiên bản mới, dropdown version hiện thêm 1 entry
- [ ] Rollback chọn version cũ → content textarea đổi về bản đó
- [ ] Modal sync cảnh hoạt động: Cancel giữ cảnh cũ, Confirm re-parse và update scenes
- [ ] Không có lỗi console sau khi implement

---

## Risk Assessment

| Risk | Xác suất | Mitigation |
|------|----------|------------|
| modal-overlay CSS chưa có | Trung bình | Kiểm tra index.css, thêm nếu cần |
| Conflict giữa `generated` state (gen mới) và `activeScript` (từ DB) | Cao | Ưu tiên activeScript; sau khi gen mới thành công → cũng gọi loadSavedScripts |
| Textarea quá dài không scroll | Thấp | Thêm `maxHeight` + `overflowY: auto` |

---

## Next Steps

→ Phase 3: Test integration end-to-end
