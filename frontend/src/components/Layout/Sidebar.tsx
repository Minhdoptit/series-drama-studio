import { NavLink, useNavigate, useParams } from 'react-router-dom'
import { FileText, Image, Film, Settings, FolderOpen, LogOut, Users } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { projectId, epId } = useParams<{ projectId?: string; epId?: string }>()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? 'U'

  const inEpisode = !!projectId && !!epId

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Film size={18} color="var(--accent)" />
          Drama Studio
        </div>
      </div>

      <nav className="sidebar-nav">
        {/* Luôn hiển thị: Dự án */}
        <div className="nav-section-title">Điều hướng</div>
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
        >
          <FolderOpen size={16} className="nav-icon" />
          Dự án
        </NavLink>

        {/* Hiển thị khi đang ở trong project */}
        {projectId && !epId && (
          <NavLink
            to={`/project/${projectId}`}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Film size={16} className="nav-icon" />
            Các tập phim
          </NavLink>
        )}

        {/* Hiển thị khi đang ở trong tập cụ thể */}
        {inEpisode && (
          <>
            <div className="nav-section-title" style={{ marginTop: 8 }}>Tập hiện tại</div>
            <NavLink
              to={`/project/${projectId}/episode/${epId}/script`}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <FileText size={16} className="nav-icon" />
              Kịch bản
            </NavLink>
            <NavLink
              to={`/project/${projectId}/episode/${epId}/image`}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Image size={16} className="nav-icon" />
              Hình ảnh tập
            </NavLink>
            <NavLink
              to={`/project/${projectId}/episode/${epId}/video`}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Film size={16} className="nav-icon" />
              Video
            </NavLink>
            <NavLink
              to={`/project/${projectId}/characters`}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Users size={16} className="nav-icon" />
              Nhân vật chung
            </NavLink>
          </>
        )}

        {/* Characters từ project level */}
        {projectId && !epId && (
          <NavLink
            to={`/project/${projectId}/characters`}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Users size={16} className="nav-icon" />
            Nhân vật chung
          </NavLink>
        )}

        <div className="nav-section-title" style={{ marginTop: 8 }}>Tài khoản</div>
        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
        >
          <Settings size={16} className="nav-icon" />
          Cài đặt API
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="user-info" onClick={handleLogout} title="Đăng xuất">
          <div className="user-avatar">{initials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="user-name">{user?.full_name || user?.email}</div>
            <div className="user-email">{user?.email}</div>
          </div>
          <LogOut size={14} color="var(--text-muted)" />
        </div>
      </div>
    </aside>
  )
}
