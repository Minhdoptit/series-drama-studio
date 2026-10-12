import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, FolderOpen, Film, FileText, Image, Trash2, Calendar } from 'lucide-react'
import api from '../lib/api'
import toast from 'react-hot-toast'

interface Project {
  id: string
  name: string
  style: string | null
  description: string | null
  created_at: string
  updated_at: string
}

function CreateProjectModal({ onClose, onCreate }: { onClose: () => void; onCreate: (p: Project) => void }) {
  const [name, setName] = useState('')
  const [style, setStyle] = useState('3D Pixar mềm, nhân vật con vật cách điệu dáng người')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)

  const handleCreate = async () => {
    if (!name.trim()) return toast.error('Nhập tên project')
    setLoading(true)
    try {
      const { data } = await api.post('/projects', { name: name.trim(), style, description })
      onCreate(data)
      onClose()
      toast.success('Đã tạo project!')
    } catch {
      toast.error('Tạo project thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="card-title">Tạo project mới</h3>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="label">Tên project *</label>
            <input id="project-name" className="input" placeholder="Cờ Vua - Tập 1" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="form-group">
            <label className="label">Phong cách hình ảnh</label>
            <input className="input" value={style} onChange={(e) => setStyle(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="label">Mô tả (tuỳ chọn)</label>
            <textarea className="textarea" rows={2} placeholder="Mô tả ngắn về project..." value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Huỷ</button>
          <button id="create-project-btn" className="btn btn-primary" onClick={handleCreate} disabled={loading}>
            {loading ? 'Đang tạo...' : 'Tạo project'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const navigate = useNavigate()

  const [error, setError] = useState(false)

  const fetchProjects = () => {
    setLoading(true)
    setError(false)
    api.get('/projects')
      .then(({ data }) => setProjects(data))
      .catch(() => { toast.error('Không thể tải dự án'); setError(true) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchProjects() }, [])

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Xoá project này? Không thể hoàn tác.')) return
    try {
      await api.delete(`/projects/${id}`)
      setProjects((prev) => prev.filter((p) => p.id !== id))
      toast.success('Đã xoá')
    } catch {
      toast.error('Xoá thất bại')
    }
  }

  const selectProject = (id: string) => {
    navigate(`/project/${id}`)
  }

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dự án của tôi</h1>
          <p className="page-subtitle">Quản lý các dự án phim hoạt hình của bạn</p>
        </div>
        <button id="new-project-btn" className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} /> Tạo project
        </button>
      </div>

      {loading ? (
        <div className="empty-state"><div className="spinner" /></div>
      ) : error ? (
        <div className="empty-state">
          <p className="empty-state-text" style={{ color: 'var(--error)' }}>Không thể tải dự án</p>
          <p className="empty-state-sub">Kiểm tra kết nối backend và thử lại</p>
          <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={fetchProjects}>
            🔄 Thử lại
          </button>
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <FolderOpen size={48} className="empty-state-icon" />
          <p className="empty-state-text">Chưa có project nào</p>
          <p className="empty-state-sub">Bấm "Tạo project" để bắt đầu</p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => setShowModal(true)}>
            <Plus size={16} /> Tạo project đầu tiên
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {projects.map((p) => (
            <div
              key={p.id}
              className="card"
              style={{ cursor: 'pointer', transition: 'border-color 0.15s' }}
              onClick={() => selectProject(p.id)}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Film size={18} color="var(--accent)" />
                  <h4 style={{ fontSize: 15, fontWeight: 600 }}>{p.name}</h4>
                </div>
                <button
                  className="btn btn-ghost btn-icon btn-sm"
                  onClick={(e) => handleDelete(p.id, e)}
                  title="Xoá project"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              {p.style && (
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>🎨 {p.style}</p>
              )}
              {p.description && (
                <p className="truncate" style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>{p.description}</p>
              )}

              <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                  <FileText size={12} /> Script
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                  <Image size={12} /> Ảnh
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                  <Film size={12} /> Video
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                <Calendar size={12} />
                {formatDate(p.updated_at)}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <CreateProjectModal
          onClose={() => setShowModal(false)}
          onCreate={(p) => setProjects((prev) => [p, ...prev])}
        />
      )}
    </div>
  )
}
