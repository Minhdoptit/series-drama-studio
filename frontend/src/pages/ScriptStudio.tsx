import { useState, useEffect, useRef } from 'react'
import { Wand2, Save, ChevronDown, ChevronUp, Plus, X, ChevronRight, History, RotateCcw } from 'lucide-react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import DocumentUpload from '../components/ScriptStudio/DocumentUpload'
import toast from 'react-hot-toast'

interface Character { name: string; age: string; description: string }
interface Scene {
  id?: string; scene_no: number; location: string
  action_desc: string; shot_type: string; duration_sec: number; voice_over: string
}
interface ScriptVersion {
  id: string
  episode_id: string
  title: string | null
  content: string
  created_at: string
  version: number
  is_active: boolean
  scenes: Scene[]
}
interface GeneratedScript { title: string; content: string; scenes: Scene[] }
interface Doc { id: string; file_name: string; file_type: string; token_count: number }

export default function ScriptStudio() {
  const { projectId = '', epId = '' } = useParams<{ projectId: string; epId: string }>()
  const navigate = useNavigate()

  // ─── Prompt input state ───────────────────────────────────────
  const [style, setStyle] = useState('3D Pixar mềm, nhân vật con vật cách điệu dáng người')
  const [characters, setCharacters] = useState<Character[]>([{ name: 'Hươu con', age: '10', description: 'Nhân vật chính, hiếu kỳ' }])
  const [content, setContent] = useState('')
  const [durationSec, setDurationSec] = useState(50)
  const [docs, setDocs] = useState<Doc[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])

  // ─── Gen & save state ─────────────────────────────────────────
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [generated, setGenerated] = useState<GeneratedScript | null>(null)

  // ─── Script version state ──────────────────────────────────────
  const [savedScripts, setSavedScripts] = useState<ScriptVersion[]>([])
  const [activeScript, setActiveScript] = useState<ScriptVersion | null>(null)
  const [editContent, setEditContent] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  const [showVersions, setShowVersions] = useState(false)

  // ─── Sync modal state ─────────────────────────────────────────
  const [showSyncModal, setShowSyncModal] = useState(false)
  const [reparsePreview, setReparsePreview] = useState<Scene[] | null>(null)
  const [reparseLoading, setReparseLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)

  // ─── Scene expand state ───────────────────────────────────────
  const [expandedScenes, setExpandedScenes] = useState<Record<number, boolean>>({})

  const versionsRef = useRef<HTMLDivElement>(null)

  // ─── Load docs ────────────────────────────────────────────────
  useEffect(() => {
    if (!projectId) return
    api.get(`/projects/${projectId}/documents`).then(({ data }) => setDocs(data)).catch(() => {})
  }, [projectId])

  // ─── Load saved scripts ───────────────────────────────────────
  const loadSavedScripts = async () => {
    if (!projectId || !epId) return
    try {
      const { data } = await api.get(`/projects/${projectId}/episodes/${epId}/scripts`)
      setSavedScripts(data)
      const active = data.find((s: ScriptVersion) => s.is_active)
      if (active) {
        setActiveScript(active)
        setEditContent(active.content)
        setIsDirty(false)
      }
    } catch { /* silent — tập có thể chưa có kịch bản */ }
  }

  useEffect(() => { loadSavedScripts() }, [projectId, epId])

  // ─── Track dirty ─────────────────────────────────────────────
  useEffect(() => {
    setIsDirty(editContent !== (activeScript?.content ?? ''))
  }, [editContent, activeScript])

  // ─── Close version dropdown on outside click ──────────────────
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (versionsRef.current && !versionsRef.current.contains(e.target as Node)) {
        setShowVersions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ─── Character helpers ────────────────────────────────────────
  const addCharacter = () => setCharacters([...characters, { name: '', age: '', description: '' }])
  const removeCharacter = (i: number) => setCharacters(characters.filter((_, idx) => idx !== i))
  const updateCharacter = (i: number, field: keyof Character, val: string) =>
    setCharacters(characters.map((c, idx) => idx === i ? { ...c, [field]: val } : c))

  // ─── Generate kịch bản mới ───────────────────────────────────
  const handleGenerate = async () => {
    if (!projectId) return toast.error('Chọn project trước (vào Dashboard)')
    if (!content.trim()) return toast.error('Nhập nội dung tập phim')
    setLoading(true)
    try {
      const { data } = await api.post(`/projects/${projectId}/episodes/${epId}/scripts/generate`, {
        style, characters, content, duration_sec: durationSec, document_ids: selectedDocIds,
      })
      setGenerated(data)
      setEditContent(data.content)
      toast.success(`Gen xong! ${data.scenes?.length || 0} cảnh`)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Gen kịch bản thất bại'
      if (msg.includes('API key') || msg.includes('Cài đặt')) {
        toast.error(
          () => <span>{msg} — <b style={{cursor:'pointer', textDecoration:'underline'}} onClick={() => navigate('/settings')}>Vào Cài đặt</b></span>,
          { duration: 6000 }
        )
      } else {
        toast.error(msg, { duration: 5000 })
      }
    } finally {
      setLoading(false)
    }
  }

  // ─── Lưu kịch bản (tạo phiên bản mới) ───────────────────────
  const handleSave = async () => {
    const hasContent = activeScript || generated
    if (!hasContent) return

    const contentToSave = editContent || generated?.content || ''
    const titleToSave = activeScript?.title || generated?.title
    // Scenes chỉ gửi khi gen mới (chưa có activeScript)
    const scenesToSave = !activeScript ? (generated?.scenes ?? []) : []

    setSaving(true)
    try {
      await api.post(`/projects/${projectId}/episodes/${epId}/scripts/save`, {
        title: titleToSave,
        content: contentToSave,
        scenes: scenesToSave,
      })
      await loadSavedScripts()
      setGenerated(null)
      setShowSyncModal(true)
      toast.success('Đã lưu kịch bản!')
    } catch {
      toast.error('Lưu thất bại')
    } finally {
      setSaving(false)
    }
  }

  // ─── Rollback: activate phiên bản cũ ─────────────────────────
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

  // ─── Reparse: preview cảnh mới từ AI ─────────────────────────
  const handleReparse = async () => {
    if (!activeScript) return
    setReparseLoading(true)
    try {
      const { data } = await api.post(
        `/projects/${projectId}/episodes/${epId}/scripts/${activeScript.id}/reparse-scenes`
      )
      setReparsePreview(data.scenes)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Parse cảnh thất bại')
    } finally {
      setReparseLoading(false)
    }
  }

  // ─── Confirm reparse: apply vào DB ───────────────────────────
  const handleConfirmReparse = async () => {
    if (!activeScript || !reparsePreview) return
    setConfirming(true)
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
    } finally {
      setConfirming(false)
    }
  }

  const closeSyncModal = () => {
    setShowSyncModal(false)
    setReparsePreview(null)
  }

  // ─── Scenes để hiển thị ──────────────────────────────────────
  const scenesToShow = activeScript?.scenes ?? generated?.scenes ?? []
  const canSave = (activeScript && isDirty) || (!activeScript && generated)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Studio Kịch Bản</h1>
          <p className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ cursor: 'pointer', color: 'var(--accent)' }} onClick={() => navigate(`/project/${projectId}`)}>Dự án</span>
            <ChevronRight size={12} />
            <span>Tập — Kịch bản</span>
          </p>
        </div>
        {canSave && (
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={16} />
            {saving ? 'Đang lưu...' : 'Lưu kịch bản'}
          </button>
        )}
      </div>

      <div className="two-col">
        {/* ─── Left: Prompt Input ─── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Thông tin kịch bản</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="form-group">
                <label className="label">Phong cách hình ảnh</label>
                <input className="input" value={style} onChange={(e) => setStyle(e.target.value)} placeholder="3D Pixar, anime, live action..." />
              </div>

              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <label className="label" style={{ margin: 0 }}>Nhân vật</label>
                  <button className="btn btn-ghost btn-sm" onClick={addCharacter}>
                    <Plus size={14} /> Thêm
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {characters.map((c, i) => (
                    <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 60px 1fr auto', gap: 6, alignItems: 'center' }}>
                      <input className="input" placeholder="Tên nhân vật" value={c.name} onChange={(e) => updateCharacter(i, 'name', e.target.value)} />
                      <input className="input" placeholder="Tuổi" value={c.age} onChange={(e) => updateCharacter(i, 'age', e.target.value)} />
                      <input className="input" placeholder="Mô tả ngắn" value={c.description} onChange={(e) => updateCharacter(i, 'description', e.target.value)} />
                      <button className="btn btn-ghost btn-icon btn-sm" onClick={() => removeCharacter(i)}>
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="label">Nội dung tập phim *</label>
                <textarea
                  className="textarea"
                  rows={5}
                  placeholder="Mô tả nội dung, tình tiết chính, cảm xúc muốn truyền tải..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="label">Thời lượng mục tiêu (giây)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input
                    type="range" min={20} max={180} step={5} value={durationSec}
                    onChange={(e) => setDurationSec(Number(e.target.value))}
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: 14, fontWeight: 600, minWidth: 40 }}>{durationSec}s</span>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">📎 Tài liệu tham khảo</span>
            </div>
            <DocumentUpload
              projectId={projectId}
              docs={docs}
              onDocsChange={setDocs}
              selectedIds={selectedDocIds}
              onSelectChange={setSelectedDocIds}
            />
          </div>

          <button
            id="gen-script-btn"
            className="btn btn-primary"
            style={{ height: 44, fontSize: 15 }}
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : <Wand2 size={18} />}
            {loading ? 'Đang gen kịch bản...' : '🤖 Gen Kịch Bản'}
          </button>
        </div>

        {/* ─── Right: Output ─── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {!activeScript && !generated ? (
            <div className="card" style={{ minHeight: 400 }}>
              <div className="empty-state" style={{ height: '100%' }}>
                <Wand2 size={40} className="empty-state-icon" />
                <p className="empty-state-text">Kịch bản sẽ hiển thị ở đây</p>
                <p className="empty-state-sub">Điền thông tin và bấm Gen</p>
              </div>
            </div>
          ) : (
            <>
              {/* ─── Script Editor Card ─── */}
              <div className="card">
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <h3 className="card-title">
                      📄 {activeScript?.title || generated?.title || 'Kịch bản'}
                    </h3>
                    {activeScript && (
                      <span className="badge badge-blue">v{activeScript.version}</span>
                    )}
                    {isDirty && activeScript && (
                      <span className="badge-warning">✏️ chưa lưu</span>
                    )}
                  </div>

                  {/* Version history dropdown */}
                  {savedScripts.length > 0 && (
                    <div style={{ position: 'relative' }} ref={versionsRef}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setShowVersions(!showVersions)}
                        title="Lịch sử phiên bản"
                      >
                        <History size={14} />
                        Lịch sử ({savedScripts.length})
                      </button>

                      {showVersions && (
                        <div
                          className="card"
                          style={{
                            position: 'absolute', right: 0, top: '100%', marginTop: 4,
                            width: 280, zIndex: 100, padding: 6,
                            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                          }}
                        >
                          {savedScripts.map(s => (
                            <div
                              key={s.id}
                              className={`version-item${s.is_active ? ' active' : ''}`}
                              onClick={() => !s.is_active && handleActivate(s.id)}
                              title={s.is_active ? 'Phiên bản đang dùng' : 'Click để khôi phục'}
                            >
                              <div>
                                <span style={{ fontWeight: 500 }}>v{s.version}</span>
                                <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                                  {new Date(s.created_at).toLocaleString('vi-VN')}
                                </span>
                              </div>
                              {s.is_active
                                ? <span className="badge-active">● active</span>
                                : <RotateCcw size={12} style={{ color: 'var(--text-muted)' }} />
                              }
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Editable textarea */}
                <textarea
                  className="textarea script-editor"
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  placeholder="Nội dung kịch bản..."
                  rows={14}
                />
              </div>

              {/* ─── Scenes List ─── */}
              {scenesToShow.length > 0 && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">📋 Danh sách cảnh</h3>
                    <span className="badge badge-blue">{scenesToShow.length} cảnh</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {scenesToShow.map((scene, i) => (
                      <div
                        key={scene.id || i}
                        className="scene-row"
                        onClick={() => setExpandedScenes((prev) => ({ ...prev, [i]: !prev[i] }))}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="scene-row-header">
                          <div className="scene-no">{scene.scene_no}</div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 500 }}>{scene.location}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                              {scene.shot_type} · {scene.duration_sec}s
                            </div>
                          </div>
                          {expandedScenes[i] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
                        {expandedScenes[i] && (
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginTop: 6, paddingLeft: 40 }}>
                            <div>{scene.action_desc}</div>
                            {scene.voice_over && (
                              <div style={{ marginTop: 6, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                🎙 {scene.voice_over}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ─── Sync Modal ─── */}
      {showSyncModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeSyncModal()}>
          <div className="modal">
            {!reparsePreview ? (
              <>
                <p className="modal-title">✅ Đã lưu kịch bản thành công</p>
                <div className="modal-body">
                  <p>Bạn có muốn cập nhật <strong>danh sách cảnh</strong> từ nội dung kịch bản mới không?</p>
                  <p style={{ marginTop: 8, color: 'var(--warning)', fontSize: 13 }}>
                    ⚠️ Cảnh cũ (kể cả cảnh đã gán ảnh) sẽ bị thay thế.
                  </p>
                </div>
                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={closeSyncModal}>
                    Không, giữ cảnh cũ
                  </button>
                  <button className="btn btn-primary" onClick={handleReparse} disabled={reparseLoading}>
                    {reparseLoading ? <span className="spinner" /> : null}
                    {reparseLoading ? 'Đang phân tích...' : 'Cập nhật cảnh'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="modal-title">📋 Preview danh sách cảnh mới</p>
                <div className="modal-body">
                  <p>Tìm thấy <strong>{reparsePreview.length} cảnh</strong> từ kịch bản:</p>
                  <div style={{
                    maxHeight: 220, overflowY: 'auto', marginTop: 10,
                    border: '1px solid var(--border)', borderRadius: 6, padding: 4,
                  }}>
                    {reparsePreview.map((s, i) => (
                      <div key={i} style={{
                        padding: '5px 8px', fontSize: 12,
                        borderBottom: i < reparsePreview.length - 1 ? '1px solid var(--border)' : 'none',
                        color: 'var(--text-secondary)',
                      }}>
                        <strong style={{ color: 'var(--text-primary)' }}>C{s.scene_no}</strong>
                        {' · '}{s.location}{' · '}{s.duration_sec}s
                      </div>
                    ))}
                  </div>
                </div>
                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={closeSyncModal} disabled={confirming}>
                    Hủy
                  </button>
                  <button className="btn btn-primary" onClick={handleConfirmReparse} disabled={confirming}>
                    {confirming ? <span className="spinner" /> : null}
                    {confirming ? 'Đang cập nhật...' : `✓ Xác nhận ${reparsePreview.length} cảnh`}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
