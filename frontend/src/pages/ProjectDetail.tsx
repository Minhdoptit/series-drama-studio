import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Film, FileText, Image, Plus, Trash2, Users } from 'lucide-react'
import api from '../lib/api'
import toast from 'react-hot-toast'

interface Episode {
  id: string
  project_id: string
  ep_no: number
  title: string
  description?: string
  created_at: string
  has_script: boolean
}

interface Project {
  id: string
  name: string
  style?: string
  description?: string
}

type Tab = 'episodes' | 'characters'

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('episodes')
  const [showModal, setShowModal] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!projectId) return
    Promise.all([
      api.get(`/projects/${projectId}`),
      api.get(`/projects/${projectId}/episodes`),
    ])
      .then(([pRes, epRes]) => {
        setProject(pRes.data)
        setEpisodes(epRes.data)
      })
      .catch(() => toast.error('Không thể tải dữ liệu'))
      .finally(() => setLoading(false))
  }, [projectId])

  const handleCreateEpisode = async () => {
    if (!newTitle.trim()) return toast.error('Nhập tên tập')
    setCreating(true)
    try {
      const { data } = await api.post(`/projects/${projectId}/episodes`, {
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
      })
      setEpisodes(prev => [...prev, data])
      setShowModal(false)
      setNewTitle('')
      setNewDesc('')
      toast.success(`Đã tạo Tập ${data.ep_no}!`)
    } catch {
      toast.error('Tạo tập thất bại')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteEpisode = async (ep: Episode, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm(`Xoá "${ep.title}"? Kịch bản và video trong tập cũng bị xoá.`)) return
    try {
      await api.delete(`/projects/${projectId}/episodes/${ep.id}`)
      setEpisodes(prev => prev.filter(e => e.id !== ep.id))
      toast.success('Đã xoá tập')
    } catch {
      toast.error('Xoá thất bại')
    }
  }

  const goToEpisode = (ep: Episode) => {
    navigate(`/project/${projectId}/episode/${ep.id}/script`)
  }

  const goToCharacters = () => {
    navigate(`/project/${projectId}/characters`)
  }

  if (loading) return <div className="page-container"><div className="empty-state"><div className="spinner" /></div></div>

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{project?.name || 'Dự án'}</h1>
          <p className="page-subtitle">{project?.description || project?.style || 'Quản lý các tập phim'}</p>
        </div>
        <button id="create-episode-btn" className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} /> Thêm tập
        </button>
      </div>

      {/* Tabs */}
      <div className="tab-bar">
        <button
          className={`tab-item${tab === 'episodes' ? ' active' : ''}`}
          onClick={() => setTab('episodes')}
        >
          <Film size={14} /> Các tập phim
          <span className="badge badge-gray" style={{ marginLeft: 6 }}>{episodes.length}</span>
        </button>
        <button
          className={`tab-item${tab === 'characters' ? ' active' : ''}`}
          onClick={() => { setTab('characters'); goToCharacters() }}
        >
          <Users size={14} /> Nhân vật chung
        </button>
      </div>

      {/* Episode grid */}
      {tab === 'episodes' && (
        episodes.length === 0 ? (
          <div className="empty-state" style={{ marginTop: 40 }}>
            <Film size={48} className="empty-state-icon" />
            <p className="empty-state-text">Chưa có tập nào</p>
            <p className="empty-state-sub">Nhấn "Thêm tập" để tạo tập đầu tiên</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => setShowModal(true)}>
              <Plus size={16} /> Thêm tập đầu tiên
            </button>
          </div>
        ) : (
          <div className="project-grid">
            {episodes.map(ep => (
              <div
                key={ep.id}
                id={`episode-card-${ep.ep_no}`}
                className="card card-hover"
                onClick={() => goToEpisode(ep)}
                style={{ cursor: 'pointer' }}
              >
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8,
                      background: 'var(--accent)', display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                      color: '#fff', fontWeight: 700, fontSize: 14,
                    }}>
                      {ep.ep_no}
                    </div>
                    <div>
                      <div className="card-title" style={{ fontSize: 14 }}>{ep.title}</div>
                      {ep.description && (
                        <div className="card-subtitle truncate" style={{ maxWidth: 200 }}>{ep.description}</div>
                      )}
                    </div>
                  </div>
                  <button
                    className="btn btn-ghost btn-icon"
                    onClick={(e) => handleDeleteEpisode(ep, e)}
                    title="Xoá tập"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                {/* Status badges */}
                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  <span className={`badge ${ep.has_script ? 'badge-green' : 'badge-gray'}`}>
                    <FileText size={10} style={{ marginRight: 3 }} />
                    {ep.has_script ? 'Có kịch bản' : 'Chưa có kịch bản'}
                  </span>
                </div>

                {/* Quick links */}
                <div className="card-footer" style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ flex: 1, justifyContent: 'center' }}
                    onClick={(e) => { e.stopPropagation(); navigate(`/project/${projectId}/episode/${ep.id}/script`) }}
                  >
                    <FileText size={12} /> Kịch bản
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ flex: 1, justifyContent: 'center' }}
                    onClick={(e) => { e.stopPropagation(); navigate(`/project/${projectId}/episode/${ep.id}/image`) }}
                  >
                    <Image size={12} /> Hình ảnh
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ flex: 1, justifyContent: 'center' }}
                    onClick={(e) => { e.stopPropagation(); navigate(`/project/${projectId}/episode/${ep.id}/video`) }}
                  >
                    <Film size={12} /> Video
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Modal tạo tập */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="card-title">Thêm tập mới</h3>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="form-group">
                <label className="label">Tên tập *</label>
                <input
                  id="episode-title-input"
                  className="input"
                  placeholder="VD: Tập 1 — Ngày đầu tiên"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCreateEpisode()}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label className="label">Mô tả (tùy chọn)</label>
                <textarea
                  className="textarea"
                  rows={2}
                  placeholder="Tóm tắt nội dung tập..."
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Huỷ</button>
              <button id="confirm-create-episode" className="btn btn-primary" onClick={handleCreateEpisode} disabled={creating}>
                {creating ? 'Đang tạo...' : 'Tạo tập'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
