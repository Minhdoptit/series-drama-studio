import { useState, useEffect, useRef, useCallback } from 'react'
import { Play, Download, Film, CheckSquare, Square, AlertCircle, ChevronRight, Scissors, Plus, X as XIcon } from 'lucide-react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import toast from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** Chuyển relative /data/... path thành full URL */
const imgUrl = (url: string): string => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`
}

interface Scene {
  id: string; scene_no: number; location: string; action_desc: string
  shot_type: string; duration_sec: number; voice_over: string
  image_id: string | null; image_ids?: string[]; images?: LibImage[]; extra_prompt?: string | null
}
interface Script { id: string; title: string; scenes: Scene[] }
interface LibImage { id: string; type: string; label: string; url: string }
interface Video {
  id: string; scene_id: string; status: string
  file_path: string | null; error_msg: string | null
  started_at: string | null; completed_at: string | null
}

function ImagePickerModal({
  images,
  selectedIds,
  onSave,
  onClose
}: {
  images: LibImage[];
  selectedIds: string[];
  onSave: (selectedIds: string[]) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<string[]>(selectedIds || [])

  const toggleSelect = (id: string) => {
    if (selected.includes(id)) {
      setSelected(selected.filter((item) => item !== id))
    } else {
      setSelected([...selected, id])
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="card-title">Chọn ảnh tham chiếu (Nhiều ảnh)</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Tick chọn 1 hoặc nhiều nhân vật/bối cảnh cho cảnh này
            </p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><XIcon size={16} /></button>
        </div>
        <div className="modal-body">
          {images.length === 0 ? (
            <div className="empty-state"><p>Chưa có ảnh — vào Image Studio để gen ảnh trước</p></div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, maxHeight: 420, overflowY: 'auto', padding: 2 }}>
              {images.map((img) => {
                const isSelected = selected.includes(img.id)
                return (
                  <div
                    key={img.id}
                    style={{
                      cursor: 'pointer',
                      borderRadius: 8,
                      overflow: 'hidden',
                      border: isSelected ? '2px solid var(--accent)' : '1px solid var(--border)',
                      position: 'relative',
                      background: 'var(--bg-subtle)',
                      transition: 'all 0.15s ease',
                      boxShadow: isSelected ? '0 0 8px rgba(99, 102, 241, 0.4)' : 'none',
                    }}
                    onClick={() => toggleSelect(img.id)}
                  >
                    <div style={{ aspectRatio: '9/16', overflow: 'hidden', position: 'relative' }}>
                      <img src={imgUrl(img.url)} alt={img.label} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      <div style={{
                        position: 'absolute', top: 6, right: 6,
                        background: isSelected ? 'var(--accent)' : 'rgba(0,0,0,0.5)',
                        color: '#fff', borderRadius: 4, width: 20, height: 20,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 'bold'
                      }}>
                        {isSelected ? '✓' : ''}
                      </div>
                    </div>
                    <div style={{ padding: '4px 6px', background: 'rgba(0,0,0,0.7)', color: '#fff', fontSize: 11, textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {img.label || 'Không tên'}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setSelected([])} disabled={selected.length === 0}>
            Bỏ chọn tất cả
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary" onClick={onClose}>Hủy</button>
            <button className="btn btn-primary" onClick={() => { onSave(selected); onClose() }}>
              Xác nhận ({selected.length} ảnh)
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function VideoStudio() {
  const { projectId = '', epId = '' } = useParams<{ projectId: string; epId: string }>()
  const navigate = useNavigate()

  const [scripts, setScripts] = useState<Script[]>([])
  const [selectedScriptId, setSelectedScriptId] = useState('')
  const [scenes, setScenes] = useState<Scene[]>([])
  const [images, setImages] = useState<LibImage[]>([])
  const [checkedScenes, setCheckedScenes] = useState<Set<string>>(new Set())
  const [videos, setVideos] = useState<Record<string, Video>>({})
  const [generating, setGenerating] = useState(false)
  const [pickerScene, setPickerScene] = useState<string | null>(null)
  const [videoSize, setVideoSize] = useState('720x1280') // default 9:16
  const [duration, setDuration] = useState<number>(5) // 5s hoac 10s
  const [videoProvider, setVideoProvider] = useState<string>('kling') // video provider tu project config
  const [elapsedMap, setElapsedMap] = useState<Record<string, number>>({}) // scene_id -> seconds
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const extraPromptTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  // Merge state
  const [mergeStatus, setMergeStatus] = useState<string | null>(null)  // null | merging | done | error
  const [mergeUrl, setMergeUrl] = useState<string | null>(null)
  const [mergeError, setMergeError] = useState<string | null>(null)
  const mergePollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Ham reload videos - PHAI dinh nghia TRUOC startPolling
  const reloadVideos = useCallback(async (): Promise<Video[]> => {
    try {
      const { data } = await api.get(`/projects/${projectId}/videos`)
      const map: Record<string, Video> = {}
      data.forEach((v: Video) => { map[v.scene_id] = v })
      setVideos(map)
      return data as Video[]
    } catch {
      return []
    }
  }, [projectId])

  // startPolling phai dinh nghia truoc useEffect (tranh hoisting bug voi arrow function)
  const startPolling = useCallback((videoIds: string[]) => {
    if (pollRef.current) clearInterval(pollRef.current)
    let doneCount = 0
    pollRef.current = setInterval(async () => {
      const updates: Record<string, Video> = {}
      let allSettled = true
      for (const vid of videoIds) {
        try {
          const { data } = await api.get(`/projects/${projectId}/videos/${vid}`)
          if (data.scene_id) updates[data.scene_id] = data
          if (data.status !== 'done' && data.status !== 'error') {
            allSettled = false
          } else if (data.status === 'done') {
            doneCount++
          }
        } catch {}
      }
      if (Object.keys(updates).length > 0) {
        setVideos((prev) => ({ ...prev, ...updates }))
      }
      if (allSettled && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
        if (doneCount > 0) {
          toast.success(`${doneCount} video đã gen xong! 🎥`)
        }
        await reloadVideos()
      }
    }, 5000)
  }, [projectId, reloadVideos])

  useEffect(() => {
    if (!projectId) return
    api.get(`/projects/${projectId}/episodes/${epId}/scripts`).then(({ data }) => {
      setScripts(data)
      if (data.length > 0) {
        setSelectedScriptId(data[0].id)
        setScenes(data[0].scenes || [])
      }
    }).catch(() => {})
    api.get(`/projects/${projectId}/images`).then(({ data }) => setImages(data)).catch(() => {})
    api.get(`/projects/${projectId}/videos`).then(({ data }) => {
      const map: Record<string, Video> = {}
      data.forEach((v: Video) => { map[v.scene_id] = v })
      setVideos(map)
      // Tu dong poll neu co video dang gen - ke ca sau reload
      const activeIds = data
        .filter((v: Video) => v.status === 'running' || v.status === 'pending')
        .map((v: Video) => v.id)
      if (activeIds.length > 0) startPolling(activeIds)
    }).catch(() => {})
  }, [projectId, epId, startPolling])

  // Load config de biet video_provider (settings global, khong phai per-project)
  useEffect(() => {
    api.get('/settings/api-keys').then(({ data }) => {
      const provider = data.video_provider || 'kling'
      setVideoProvider(provider)
      // Neu dung Gemini/Veo3: lock duration = 8
      if (provider === 'gemini') setDuration(8)
    }).catch(() => {})
  }, [])


  // Load existing merge status on mount
  useEffect(() => {
    if (!projectId || !epId) return
    api.get(`/projects/${projectId}/episodes/${epId}/videos/merge`)
      .then(({ data }) => {
        setMergeStatus(data.status)
        if (data.url) setMergeUrl(`${API_BASE}${data.url}`)
        if (data.error) setMergeError(data.error)
      }).catch(() => {})
  }, [projectId, epId])

  // Dọn mọi interval/timeout khi rời trang — nếu không chúng chạy mãi và
  // tiếp tục gọi API sau khi component đã unmount.
  useEffect(() => {
    const timers = extraPromptTimers.current
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (elapsedRef.current) clearInterval(elapsedRef.current)
      if (mergePollRef.current) clearInterval(mergePollRef.current)
      Object.values(timers).forEach(clearTimeout)
    }
  }, [])

  // Elapsed timer: cập nhật mỗi 1 giây cho video đang running
  useEffect(() => {
    if (elapsedRef.current) clearInterval(elapsedRef.current)
    const runningVideos = Object.values(videos).filter(v => v.status === 'running' && v.started_at)
    if (runningVideos.length === 0) return

    elapsedRef.current = setInterval(() => {
      const now = Date.now()
      setElapsedMap(prev => {
        const next = { ...prev }
        runningVideos.forEach(v => {
          if (v.started_at) {
            next[v.scene_id] = Math.floor((now - new Date(v.started_at).getTime()) / 1000)
          }
        })
        return next
      })
    }, 1000)

    return () => { if (elapsedRef.current) clearInterval(elapsedRef.current) }
  }, [videos])

  const handleMerge = async () => {
    const doneCount = Object.values(videos).filter(v => v.status === 'done').length
    if (doneCount === 0) return toast.error('Chưa có video cảnh nào xong để ghép')
    if (!confirm(`Ghép ${doneCount} video thành 1 tập hoàn chỉnh?`)) return
    setMergeStatus('merging')
    setMergeUrl(null)
    setMergeError(null)
    try {
      await api.post(`/projects/${projectId}/episodes/${epId}/videos/merge`)
      toast.success('Đang ghép video...')
      startMergePolling()
    } catch (err: any) {
      setMergeStatus('error')
      toast.error(err.response?.data?.detail || 'Ghép video thất bại')
    }
  }

  const stopMergePolling = () => {
    if (mergePollRef.current) {
      clearInterval(mergePollRef.current)
      mergePollRef.current = null
    }
  }

  const startMergePolling = () => {
    stopMergePolling()
    mergePollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/projects/${projectId}/episodes/${epId}/videos/merge`)
        setMergeStatus(data.status)
        if (data.url) { setMergeUrl(`${API_BASE}${data.url}`); stopMergePolling(); toast.success('Ghép xong! Tải về ngay ↓') }
        if (data.error) { setMergeError(data.error); stopMergePolling() }
      } catch {}
    }, 5000)
  }

  const selectScript = (id: string) => {
    setSelectedScriptId(id)
    const sc = scripts.find((s) => s.id === id)
    setScenes(sc?.scenes || [])
    setCheckedScenes(new Set())
  }

  const toggleCheck = (id: string) => {
    setCheckedScenes((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (checkedScenes.size === scenes.length) setCheckedScenes(new Set())
    else setCheckedScenes(new Set(scenes.map((s) => s.id)))
  }

  const getSceneImages = (scene: Scene): LibImage[] => {
    if (scene.images && scene.images.length > 0) {
      return scene.images.map((img: any) => ({
        id: img.id,
        label: img.label || 'Không tên',
        type: img.type || 'character',
        url: img.file_path || img.url
      }))
    }
    const ids = scene.image_ids && scene.image_ids.length > 0 ? scene.image_ids : (scene.image_id ? [scene.image_id] : [])
    return ids.map(id => images.find(img => img.id === id)).filter(Boolean) as LibImage[]
  }

  const handleUpdateSceneImages = async (sceneId: string, newImageIds: string[]) => {
    try {
      await api.patch(`/projects/${projectId}/scenes/${sceneId}`, { image_ids: newImageIds })
      setScenes((prev) =>
        prev.map((s) => {
          if (s.id === sceneId) {
            const updatedImgs = newImageIds.map(id => images.find(img => img.id === id)).filter(Boolean) as LibImage[]
            return { ...s, image_ids: newImageIds, image_id: newImageIds[0] || null, images: updatedImgs }
          }
          return s
        })
      )
      toast.success('Đã cập nhật ảnh tham chiếu!')
    } catch {
      toast.error('Cập nhật ảnh thất bại')
    }
  }

  const handleRemoveImageFromScene = (scene: Scene, imgIdToRemove: string) => {
    const currentImages = getSceneImages(scene)
    const nextIds = currentImages.filter(img => img.id !== imgIdToRemove).map(img => img.id)
    handleUpdateSceneImages(scene.id, nextIds)
  }

  /**
   * Cập nhật prompt phụ của cảnh: đổi state ngay cho mượt, rồi PATCH lên server
   * sau 600ms ngừng gõ. Trước đây hàm này chỉ setState nên prompt không bao giờ
   * được lưu — backend đọc extra_prompt từ DB nên luôn nhận null.
   */
  const setExtraPrompt = (sceneId: string, val: string) => {
    setScenes((prev) => prev.map((s) => s.id === sceneId ? { ...s, extra_prompt: val } : s))

    const timers = extraPromptTimers.current
    if (timers[sceneId]) clearTimeout(timers[sceneId])
    timers[sceneId] = setTimeout(async () => {
      delete timers[sceneId]
      try {
        await api.patch(`/projects/${projectId}/scenes/${sceneId}`, { extra_prompt: val })
      } catch {
        toast.error('Không lưu được prompt cho cảnh này')
      }
    }, 600)
  }

  const handleGenerate = async () => {
    if (checkedScenes.size === 0) return toast.error('Chọn ít nhất 1 cảnh')
    if (!confirm(`Gen video ${checkedScenes.size} cảnh đã chọn?`)) return
    setGenerating(true)
    try {
      const { data } = await api.post(`/projects/${projectId}/videos/generate`, {
        scene_ids: Array.from(checkedScenes),
        video_size: videoSize,
        duration: duration,
      })
      toast.success(data.message)
      // Reload ngay de hien trang thai pending trong scene card
      const allVideos = await reloadVideos()
      // Bat dau poll cac video moi gen
      if (data.video_ids?.length > 0) {
        startPolling(data.video_ids)
      } else {
        // Fallback: poll cac video pending/running moi nhat
        const activeIds = allVideos
          .filter((v: Video) => v.status === 'running' || v.status === 'pending')
          .map((v: Video) => v.id)
        if (activeIds.length > 0) startPolling(activeIds)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Gen video thất bại')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Studio Video</h1>
          <p className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ cursor: 'pointer', color: 'var(--accent)' }} onClick={() => navigate(`/project/${projectId}`)}>Dự án</span>
            <ChevronRight size={12} />
            <span>Tập — Video</span>
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Ratio + resolution picker.
              Với Veo, độ phân giải quyết định giá theo giây (720p rẻ nhất, 4K đắt
              nhất) nên nhãn phải ghi rõ. Nhãn cũ ghi "4:5" cho 1080x1920 là sai —
              kích thước đó là 9:16 ở mức 1080p. */}
          {([
            { label: '9:16', size: '720x1280',  icon: '▯', quality: '720p' },
            { label: '9:16', size: '1080x1920', icon: '▯', quality: '1080p' },
            { label: '16:9', size: '1280x720',  icon: '▭', quality: '720p' },
            { label: '16:9', size: '3840x2160', icon: '▭', quality: '4K' },
            { label: '1:1',  size: '1024x1024', icon: '□', quality: '720p' },
          ] as { label: string; size: string; icon: string; quality: string }[]).map(({ label, size, icon, quality }) => (
            <button
              key={size}
              onClick={() => setVideoSize(size)}
              title={`Tỉ lệ ${label} · ${quality} (${size})`}
              style={{
                padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border)',
                background: videoSize === size ? 'var(--accent)' : 'var(--bg-card)',
                color: videoSize === size ? '#fff' : 'var(--text-secondary)',
                fontSize: 12, cursor: 'pointer', fontWeight: videoSize === size ? 700 : 400,
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1,
                lineHeight: 1.1,
              }}
            >
              <span style={{ fontSize: 10 }}>{icon} {label}</span>
              <span style={{ fontSize: 9, opacity: 0.85 }}>{quality}</span>
            </button>
          ))}

          {/* Duration picker */}
          <div style={{ display: 'flex', gap: 2, background: 'var(--bg-subtle)', padding: 2, borderRadius: 6, border: '1px solid var(--border)', marginLeft: 4 }}>
            {videoProvider === 'gemini' ? (
              // Gemini/Veo3: chi ho tro 8s
              <span style={{
                padding: '4px 10px', borderRadius: 4,
                background: 'var(--accent)', color: '#fff',
                fontSize: 12, fontWeight: 700,
                display: 'flex', alignItems: 'center', gap: 4, height: 36,
              }}>
                ⏱️ 8s
              </span>
            ) : (
              [5, 10].map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  title={`Thời lượng video ${d} giây`}
                  style={{
                    padding: '4px 10px', borderRadius: 4, border: 'none',
                    background: duration === d ? 'var(--accent)' : 'transparent',
                    color: duration === d ? '#fff' : 'var(--text-secondary)',
                    fontSize: 12, cursor: 'pointer', fontWeight: duration === d ? 700 : 500,
                    display: 'flex', alignItems: 'center', gap: 4, height: 36,
                  }}
                >
                  ⏱️ {d}s
                </button>
              ))
            )}
          </div>
          <button
            id="gen-video-btn"
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={generating || checkedScenes.size === 0}
          >
            {generating ? <span className="spinner" /> : <Film size={16} />}
            {generating ? 'Đang gen...' : `⚡ Gen ${checkedScenes.size || ''} video`}
          </button>
          <button
            id="merge-video-btn"
            className={`btn ${mergeStatus === 'done' ? 'btn-success' : 'btn-secondary'}`}
            onClick={mergeStatus === 'done' && mergeUrl ? () => window.open(mergeUrl, '_blank') : handleMerge}
            disabled={mergeStatus === 'merging'}
            title={mergeStatus === 'error' ? mergeError || '' : ''}
          >
            {mergeStatus === 'merging' ? <span className="spinner" /> : <Scissors size={16} />}
            {mergeStatus === 'merging' ? 'Đang ghép...' : mergeStatus === 'done' ? '▶ Xem tập đã ghép' : '🎥 Ghép Tập'}
          </button>
        </div>
      </div>

      {/* Script selector */}
      {scripts.length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <label className="label">Chọn kịch bản</label>
          <select className="select" style={{ maxWidth: 400 }} value={selectedScriptId} onChange={(e) => selectScript(e.target.value)}>
            {scripts.map((s) => <option key={s.id} value={s.id}>{s.title || 'Kịch bản ' + s.id.slice(0, 6)}</option>)}
          </select>
        </div>
      )}

      {scenes.length === 0 ? (
        <div className="empty-state">
          <Film size={48} className="empty-state-icon" />
          <p className="empty-state-text">Chưa có cảnh nào</p>
          <p className="empty-state-sub">Vào Script Studio để gen kịch bản trước</p>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <button className="btn btn-ghost btn-sm" onClick={toggleAll}>
              {checkedScenes.size === scenes.length ? <CheckSquare size={14} /> : <Square size={14} />}
              {checkedScenes.size === scenes.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
            </button>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Đã chọn: {checkedScenes.size}/{scenes.length} cảnh
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {scenes.map((scene) => {
              const video = videos[scene.id]
              const sceneImages = getSceneImages(scene)
              const isChecked = checkedScenes.has(scene.id)

              return (
                <div key={scene.id} className={`scene-row${isChecked ? ' selected' : ''}`}>
                  <div className="scene-row-header">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleCheck(scene.id)}
                      style={{ flexShrink: 0 }}
                    />
                    <div className="scene-no">{scene.scene_no}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 500, fontSize: 13 }}>{scene.location}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {scene.shot_type} · {scene.duration_sec}s
                      </div>
                    </div>

                    {/* Multi-reference image picker */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                      {sceneImages.map((refImage, idx) => (
                        <div
                          key={refImage.id || idx}
                          style={{
                            width: 42, height: 60, borderRadius: 6, overflow: 'hidden',
                            border: '1px solid var(--accent)', position: 'relative',
                            background: 'var(--bg-subtle)', flexShrink: 0,
                          }}
                          title={`Ảnh #${idx+1}: ${refImage.label || 'Không nhãn'}`}
                        >
                          <img src={imgUrl(refImage.url)} alt={refImage.label} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          <div style={{
                            position: 'absolute', bottom: 0, left: 0, right: 0,
                            background: 'rgba(0,0,0,0.75)', color: '#fff', fontSize: 9,
                            padding: '1px 2px', textAlign: 'center', whiteSpace: 'nowrap',
                            overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600,
                          }}>
                            {refImage.label || `Ảnh ${idx+1}`}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRemoveImageFromScene(scene, refImage.id);
                            }}
                            title="Xóa ảnh này khỏi cảnh"
                            style={{
                              position: 'absolute', top: 2, right: 2,
                              background: 'rgba(0,0,0,0.75)', color: '#fff',
                              border: 'none', borderRadius: '50%', width: 15, height: 15,
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 10, cursor: 'pointer', padding: 0, lineHeight: 1
                            }}
                          >
                            ×
                          </button>
                        </div>
                      ))}

                      <button
                        style={{
                          width: 42, height: 60, borderRadius: 6,
                          border: '1px dashed var(--border)', cursor: 'pointer',
                          background: 'var(--bg-subtle)', flexShrink: 0,
                          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                          gap: 2, color: 'var(--text-muted)', fontSize: 10,
                        }}
                        onClick={() => setPickerScene(scene.id)}
                        title="Thêm hoặc sửa ảnh tham chiếu cho cảnh này"
                      >
                        <Plus size={14} color="var(--text-muted)" />
                        <span>+ Ảnh</span>
                      </button>
                    </div>

                    {/* Video status + player */}
                    {video && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                        <div className={`status-dot status-${video.status}`} />
                        {video.status === 'done' && video.file_path && (
                          <>
                            <a href={`${API_BASE}${video.file_path}`} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm">
                              <Play size={12} /> Xem
                            </a>
                            <a href={`${API_BASE}/projects/${projectId}/videos/${video.id}/download`} download className="btn btn-ghost btn-sm" title="Tải video cảnh này">
                              <Download size={12} />
                            </a>
                          </>
                        )}
                        {video.status === 'running' && (
                          <span style={{ fontSize: 11, color: 'var(--accent)' }}>⚡ Đang gen...</span>
                        )}
                        {video.status === 'pending' && (
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>⏳ Chờ gen...</span>
                        )}
                        {video.status === 'error' && (
                          <span style={{ fontSize: 11, color: 'var(--error)', display: 'flex', alignItems: 'center', gap: 4 }} title={video.error_msg || 'Gen thất bại'}>
                            <AlertCircle size={14} color="var(--error)" />
                            <span>{video.error_msg ? (video.error_msg.length > 50 ? `${video.error_msg.slice(0, 50)}...` : video.error_msg) : 'Gen lỗi'}</span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Inline video player khi done */}
                  {video?.status === 'done' && video.file_path && (
                    <div style={{ paddingLeft: 60, marginTop: 8 }}>
                      <video
                        src={`${API_BASE}${video.file_path}`}
                        controls
                        style={{
                          width: '100%', maxWidth: 280, borderRadius: 8,
                          border: '1px solid var(--border)', background: '#000',
                        }}
                      />
                    </div>
                  )}

                  <div style={{ paddingLeft: 60, marginTop: 6 }}>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>{scene.action_desc}</p>
                    <input
                      className="input"
                      style={{ fontSize: 12, height: 30 }}
                      placeholder="Thêm prompt cho video này (tuỳ chọn)..."
                      value={scene.extra_prompt || ''}
                      onChange={(e) => setExtraPrompt(scene.id, e.target.value)}
                    />
                  </div>

                  {video?.status === 'running' && (() => {
                    const AVG_SEC = 3 * 60 // ước tính 3 phút
                    const elapsed = elapsedMap[scene.id] ?? 0
                    const pct = Math.min((elapsed / AVG_SEC) * 100, 92)
                    const mins = Math.floor(elapsed / 60)
                    const secs = elapsed % 60
                    const elapsedStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
                    return (
                      <div style={{ paddingLeft: 60, marginTop: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Đang gen video...</span>
                          <span style={{ fontSize: 11, color: 'var(--accent)', fontVariantNumeric: 'tabular-nums' }}>⏱ {elapsedStr}</span>
                        </div>
                        <div className="progress">
                          <div className="progress-fill" style={{ width: `${pct}%`, transition: 'width 1s linear' }} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 2 }}>
                          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{Math.round(pct)}%</span>
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )
            })}
          </div>
        </>
      )}

      {pickerScene && (
        <ImagePickerModal
          images={images}
          selectedIds={getSceneImages(scenes.find((s) => s.id === pickerScene)!).map((img) => img.id)}
          onSave={(selectedIds) => handleUpdateSceneImages(pickerScene, selectedIds)}
          onClose={() => setPickerScene(null)}
        />
      )}

      {/* Merged episode video banner */}
      {(mergeStatus === 'done' || mergeStatus === 'error') && (
        <div className="card" style={{
          marginTop: 24,
          border: mergeStatus === 'done' ? '1px solid var(--success)' : '1px solid var(--error)',
          background: mergeStatus === 'done' ? 'rgba(34,197,94,0.05)' : 'rgba(239,68,68,0.05)',
        }}>
          <div className="card-header">
            <h3 className="card-title">
              {mergeStatus === 'done' ? '🎥 Video toàn tập đã ghép xong' : '⚠️ Ghép video thất bại'}
            </h3>
            {mergeStatus === 'done' && mergeUrl && (
              <div style={{ display: 'flex', gap: 8 }}>
                <a href={mergeUrl} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
                  <Play size={14} /> Xem
                </a>
                <a
                  href={`${API_BASE}/projects/${projectId}/episodes/${epId}/videos/download`}
                  download={`episode_${epId.slice(0,8)}.mp4`}
                  className="btn btn-primary btn-sm"
                >
                  <Download size={14} /> Tải toàn tập
                </a>
              </div>
            )}
          </div>
          {mergeStatus === 'error' && (
            <p style={{ fontSize: 13, color: 'var(--error)', padding: '0 16px 16px' }}>{mergeError}</p>
          )}
          {mergeStatus === 'done' && mergeUrl && (
            <div style={{ padding: '0 16px 16px' }}>
              <video
                src={mergeUrl}
                controls
                style={{ width: '100%', maxHeight: 400, borderRadius: 8, background: '#000' }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
