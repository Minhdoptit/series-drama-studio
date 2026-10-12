import { create } from 'zustand'
import api from '../lib/api'

interface User {
  id: string
  email: string
  full_name: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name: string) => Promise<void>
  logout: () => void
  loadFromStorage: () => void
}

// ─── Cookie helpers ───────────────────────────────────────────────────────────
const COOKIE_TOKEN = 'ds_token'
const COOKIE_USER  = 'ds_user'
const COOKIE_TTL   = 7 // ngày

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString()
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Strict`
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Strict`
}

// Doc token ngay khi khoi tao store (synchronous) de tranh race condition
const _storedToken = getCookie(COOKIE_TOKEN)
const _storedUser = (() => {
  try { return JSON.parse(getCookie(COOKIE_USER) || 'null') } catch { return null }
})()

export const useAuthStore = create<AuthState>((set) => ({
  user: _storedUser,
  token: _storedToken,
  isLoading: false,

  loadFromStorage: () => {
    const token = getCookie(COOKIE_TOKEN)
    const userStr = getCookie(COOKIE_USER)
    if (token && userStr) {
      try { set({ token, user: JSON.parse(userStr) }) } catch {}
    }
  },

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/auth/login', { email, password })
      const user = { id: data.user_id, email: data.email, full_name: data.full_name }
      setCookie(COOKIE_TOKEN, data.access_token, COOKIE_TTL)
      setCookie(COOKIE_USER, JSON.stringify(user), COOKIE_TTL)
      set({ token: data.access_token, user })
    } finally {
      set({ isLoading: false })
    }
  },

  register: async (email, password, full_name) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/auth/register', { email, password, full_name })
      const user = { id: data.user_id, email: data.email, full_name: data.full_name }
      setCookie(COOKIE_TOKEN, data.access_token, COOKIE_TTL)
      setCookie(COOKIE_USER, JSON.stringify(user), COOKIE_TTL)
      set({ token: data.access_token, user })
    } finally {
      set({ isLoading: false })
    }
  },

  logout: () => {
    deleteCookie(COOKIE_TOKEN)
    deleteCookie(COOKIE_USER)
    // Xoa localStorage cu neu co
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },
}))
