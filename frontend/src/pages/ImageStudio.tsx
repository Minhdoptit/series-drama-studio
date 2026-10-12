import { useState, useEffect, useRef } from 'react'
import { Wand2, Save, RefreshCw, Trash2, ChevronRight, Pencil, Check, X as XIcon } from 'lucide-react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import toast from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** Convert relative /data/... path (from backend) thành full URL để dùng trong <img src> */
const imgUrl = (path: string): string => {
  if (!path) return ''
  if (path.startsWith('http')) return path  // URL từ provider (external)
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
}

const IMAGE_STYLES = [
  '3D Pixar mềm, nhân vật con vật cách điệu dáng người',
  'Anime phong cách Studio Ghibli',
  '2D cartoon màu sắc tươi sáng',
  'Watercolor illustration, màu nhẹ nhàng',
  'Semi-realistic 3D render',
]

const IMAGE_TYPES = [
  { value: 'character', label: 'Nhân vật' },
  { value: 'background', label: 'Bối cảnh' },
  { value: 'prop', label: 'Đạo cụ' },
]

interface SavedImage {
  id: string
  type: string
  label: string
  prompt: string
  style: string
  url: string
}

export default function ImageStudio({ shared = false }: { shared?: boolean }) {
  const { projectId = '', epId } = useParams<{ projectId: string; epId?: string }>()
  const navigate = useNavigate()
  const episodeId = shared ? undefined : epId

  const [imageType, setImageType] = useState('character')
  const [label, setLabel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [style, setStyle] = useState(IMAGE_STYLES[0])
  const [loading, setLoading] = useState(false)
  const [generatedImages, setGeneratedImages] = useState<string[]>([])
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [savedImages, setSavedImages] = useState<SavedImage[]>([])
  const [savingIdx, setSavingIdx] = useState<number | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const renameRef = useRef<HTMLInputElement>(null)

  // Phụ thuộc phải gồm cả `shared` và `epId`, nếu không thư viện ảnh sẽ giữ
  // nguyên kết quả của tập cũ khi người dùng chuyển sang tập khác.
  useEffect(() => {
    if (!projectId) return
    api.get(`/projects/${projectId}/images`, { params: shared ? { shared: true } : epId ? { episode_id: epId } : {} })
      .then(({ data }) => setSavedImages(data.map((img: SavedImage) => ({ ...img, url: imgUrl(img.url) }))))
      .catch(() => {})
  }, [projectId, epId, shared])

  const handleGenerate = async () => {
    if (!projectId) return toast.error('Chọn project trước')
    if (!prompt.trim()) return toast.error('Nhập mô tả ảnh')
    setLoading(true)
    setGeneratedImages([])
    setSelectedIdx(null)
    try {
      const { data } = await api.post(`/projects/${projectId}/images/generate`, {
        type: imageType, label, prompt, style,
        episode_id: episodeId ?? null,
      })
      setGeneratedImages(data.images || [])
      toast.success(`Gen xong ${data.images?.length || 0} ảnh!`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Gen ảnh thất bại')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (idx: number) => {
    if (!label.trim()) {
      toast.error('Hãy đặt tên ảnh trước khi lưu')
      return
    }
    setSavingIdx(idx)
    try {
      const imgSrc = generatedImages[idx]
      const isB64 = imgSrc.startsWith('data:')
      const { data } = await api.post(`/projects/${projectId}/images/save`, {
        type: imageType,
        label: label.trim(),
        prompt, style,
        episode_id: episodeId ?? null,
        ...(isB64 ? { image_b64: imgSrc.split(',')[1] } : { image_url: imgSrc }),
      })
      setSavedImages((prev) => [{ id: data.id, type: imageType, label: label.trim(), prompt, style, url: imgUrl(data.file_path) }, ...prev])
      toast.success('Đã lưu vào thư viện!')
    } catch {
      toast.error('Lưu ảnh thất bại')
    } finally {
      setSavingIdx(null)
    }
  }

  const startRename = (img: SavedImage) => {
    setRenamingId(img.id)
    setRenameValue(img.label || '')
    setTimeout(() => renameRef.current?.focus(), 50)
  }

  const cancelRename = () => {
    setRenamingId(null)
    setRenameValue('')
  }

  const confirmRename = async (id: string) => {
    if (!renameValue.trim()) return cancelRename()
    try {
      await api.patch(`/projects/${projectId}/images/${id}`, { label: renameValue.trim() })
      setSavedImages(prev => prev.map(img => img.id === id ? { ...img, label: renameValue.trim() } : img))
      toast.success('Đã đổi tên!')
    } catch {
      toast.error('Đổi tên thất bại')
    } finally {
      cancelRename()
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/projects/${projectId}/images/${id}`)
      setSavedImages((prev) => prev.filter((img) => img.id !== id))
      toast.success('Đã xoá')
    } catch {
      toast.error('Xoá thất bại')
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{shared ? 'Nhân Vật Chung' : 'Studio Hình Ảnh'}</h1>
          <p className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ cursor: 'pointer', color: 'var(--accent)' }} onClick={() => navigate(`/project/${projectId}`)}>Dự án</span>
            <ChevronRight size={12} />
            <span>{shared ? 'Nhân vật chung' : 'Hình Ảnh tập'}</span>
          </p>
        </div>
      </div>

      <div className="two-col">
        {/* ─── Left: Prompt ─── */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <h3 className="card-title">Tạo ảnh mới</h3>

          <div className="form-group">
            <label className="label">Loại ảnh</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {IMAGE_TYPES.map((t) => (
                <button
                  key={t.value}
                  className={`btn ${imageType === t.value ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => setImageType(t.value)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="label">
              Tên ảnh <span style={{ color: 'var(--error)' }}>*</span>
            </label>
            <input
              className="input"
              placeholder="VD: Hươu con mặc vest, Sảnh đăng ký rộng..."
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              Tên này sẽ hiện trong thư viện khi ghép với kịch bản
            </p>
          </div>

          <div className="form-group">
            <label className="label">Mô tả ảnh *</label>
            <textarea
              className="textarea"
              rows={4}
              placeholder="Mô tả chi tiết nhân vật hoặc bối cảnh muốn tạo..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="label">Phong cách</label>
            <select className="select" value={style} onChange={(e) => setStyle(e.target.value)}>
              {IMAGE_STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <button
            id="gen-image-btn"
            className="btn btn-primary"
            style={{ height: 42, fontSize: 15 }}
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : <Wand2 size={18} />}
            {loading ? 'Đang gen ảnh...' : '🤖 Gen 3 ảnh'}
          </button>
        </div>

        {/* ─── Right: Results + Library ─── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Generated results */}
          {(loading || generatedImages.length > 0) && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Kết quả gen</h3>
                {!loading && (
                  <button className="btn btn-ghost btn-sm" onClick={handleGenerate}>
                    <RefreshCw size={14} /> Gen lại
                  </button>
                )}
              </div>
              {loading ? (
                <div className="empty-state" style={{ padding: '40px 0' }}>
                  <div className="spinner" style={{ width: 32, height: 32 }} />
                  <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>Đang gen ảnh, vui lòng chờ...</p>
                </div>
              ) : (
                <div className="image-grid">
                  {generatedImages.map((src, idx) => (
                    <div
                      key={idx}
                      className={`image-card${selectedIdx === idx ? ' selected' : ''}`}
                      onClick={() => setSelectedIdx(idx === selectedIdx ? null : idx)}
                    >
                      <img src={src} alt={`Gen ${idx + 1}`} />
                      <div className="image-card-actions">
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ flex: 1 }}
                          onClick={(e) => { e.stopPropagation(); handleSave(idx) }}
                          disabled={savingIdx === idx}
                        >
                          {savingIdx === idx ? '...' : <><Save size={12} /> Lưu</>}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Saved library */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">🖼 Thư viện ảnh đã lưu</h3>
              <span className="badge badge-gray">{savedImages.length} ảnh</span>
            </div>
            {savedImages.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px 0' }}>
                <p className="empty-state-text">Chưa có ảnh nào được lưu</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 12 }}>
                {savedImages.map((img) => (
                  <div key={img.id} style={{ position: 'relative' }}>
                    {/* Thumbnail */}
                    <div
                      style={{
                        aspectRatio: '1/1', borderRadius: 6, overflow: 'hidden',
                        border: '1px solid var(--border)', background: 'var(--bg-subtle)',
                      }}
                    >
                      <img src={img.url} alt={img.label} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </div>

                    {/* Type badge */}
                    <span style={{
                      position: 'absolute', top: 4, left: 4,
                      background: 'rgba(0,0,0,0.55)', color: '#fff',
                      fontSize: 10, padding: '1px 5px', borderRadius: 3,
                    }}>
                      {img.type === 'character' ? 'Nhân vật' : img.type === 'background' ? 'Bối cảnh' : 'Đạo cụ'}
                    </span>

                    {/* Delete button */}
                    <button
                      className="btn btn-ghost btn-icon"
                      style={{ position: 'absolute', top: 2, right: 2, width: 22, height: 22, background: 'rgba(255,255,255,0.9)' }}
                      onClick={() => handleDelete(img.id)}
                      title="Xoá ảnh"
                    >
                      <Trash2 size={11} />
                    </button>

                    {/* Name row — click to rename */}
                    {renamingId === img.id ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 5 }}>
                        <input
                          ref={renameRef}
                          className="input"
                          style={{ fontSize: 12, height: 26, padding: '0 6px', flex: 1 }}
                          value={renameValue}
                          onChange={e => setRenameValue(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter') confirmRename(img.id)
                            if (e.key === 'Escape') cancelRename()
                          }}
                        />
                        <button
                          className="btn btn-ghost btn-icon"
                          style={{ width: 24, height: 24, color: 'var(--success)' }}
                          onClick={() => confirmRename(img.id)}
                        >
                          <Check size={12} />
                        </button>
                        <button
                          className="btn btn-ghost btn-icon"
                          style={{ width: 24, height: 24 }}
                          onClick={cancelRename}
                        >
                          <XIcon size={12} />
                        </button>
                      </div>
                    ) : (
                      <div
                        style={{
                          display: 'flex', alignItems: 'center', gap: 4,
                          marginTop: 5, cursor: 'pointer', padding: '2px 4px',
                          borderRadius: 4, border: '1px solid transparent',
                        }}
                        className="rename-row"
                        onClick={() => startRename(img)}
                        title="Click để đổi tên"
                      >
                        <span style={{
                          fontSize: 12, fontWeight: 500, color: 'var(--text-primary)',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                        }}>
                          {img.label || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>chưa đặt tên</span>}
                        </span>
                        <Pencil size={10} style={{ flexShrink: 0, color: 'var(--text-muted)' }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
