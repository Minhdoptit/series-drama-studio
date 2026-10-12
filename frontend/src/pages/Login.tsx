import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Film } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Email hoặc mật khẩu không đúng')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <Film size={32} color="var(--accent)" />
        </div>
        <h1 className="auth-title">Đăng nhập</h1>
        <p className="auth-sub">Drama Studio — Gen kịch bản, ảnh, video AI</p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="label">Email</label>
            <input
              id="email"
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
              id="password"
              type="password"
              className="input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            id="login-btn"
            type="submit"
            className="btn btn-primary w-full"
            style={{ marginTop: 8, height: 40 }}
            disabled={isLoading}
          >
            {isLoading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : null}
            {isLoading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>

        <div className="divider-label" style={{ marginTop: 24 }}>
          Chưa có tài khoản?
        </div>
        <Link to="/register">
          <button className="btn btn-secondary w-full">Đăng ký ngay</button>
        </Link>
      </div>
    </div>
  )
}
