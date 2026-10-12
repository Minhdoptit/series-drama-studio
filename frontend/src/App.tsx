import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppLayout from './components/Layout/AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ProjectDetail from './pages/ProjectDetail'
import ScriptStudio from './pages/ScriptStudio'
import ImageStudio from './pages/ImageStudio'
import VideoStudio from './pages/VideoStudio'
import Settings from './pages/Settings'
import { useAuthStore } from './store/authStore'

const queryClient = new QueryClient()

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const loadFromStorage = useAuthStore((s) => s.loadFromStorage)

  useEffect(() => {
    loadFromStorage()
  }, [loadFromStorage])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { fontSize: 14, fontFamily: 'Inter, sans-serif', borderRadius: 8, border: '1px solid var(--border)' },
            success: { iconTheme: { primary: 'var(--success)', secondary: '#fff' } },
          }}
        />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <AppLayout />
              </PrivateRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />

            {/* Project detail + episode routes */}
            <Route path="project/:projectId" element={<ProjectDetail />} />
            <Route path="project/:projectId/episode/:epId/script" element={<ScriptStudio />} />
            <Route path="project/:projectId/episode/:epId/image" element={<ImageStudio />} />
            <Route path="project/:projectId/characters" element={<ImageStudio shared />} />
            <Route path="project/:projectId/episode/:epId/video" element={<VideoStudio />} />

            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
