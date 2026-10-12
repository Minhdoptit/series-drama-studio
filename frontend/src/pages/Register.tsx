import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Film } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const { register, isLoading } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (password.length < 6) {
      toast.error('Mật khẩu phải ít nhất 6 ký tự')
      return
    }
    try {
      await register(email, password, fullName)
      toast.success('Đăng ký thành công!')
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Đăng ký thất bại')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <Film size={32} color="var(--accent)" />
        </div>
        <h1 className="auth-title">Tạo tài khoản</h1>
        <p className="auth-sub">Bắt đầu tạo nội dung phim AI</p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="label">Họ tên</label>
            <input
              id="full-name"
              type="text"
              className="input"
              placeholder="Nguyễn Văn A"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="label">Email</label>
            <input
              id="register-email"
              type="email"
              className="input"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="label">Mật khẩu</label>
            <input
              id="register-password"
              type="password"
              className="input"
              placeholder="Ít nhất 6 ký tự"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            id="register-btn"
            type="submit"
            className="btn btn-primary w-full"
            style={{ marginTop: 8, height: 40 }}
            disabled={isLoading}
          >
            {isLoading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : null}
            {isLoading ? 'Đang tạo tài khoản...' : 'Đăng ký'}
          </button>
        </form>

        <div className="divider-label" style={{ marginTop: 24 }}>
          Đã có tài khoản?
        </div>
        <Link to="/login">
          <button className="btn btn-secondary w-full">Đăng nhập</button>
        </Link>
      </div>
    </div>
  )
}
