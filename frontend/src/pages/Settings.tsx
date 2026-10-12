import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, Loader } from 'lucide-react'
import api from '../lib/api'
import toast from 'react-hot-toast'

const PROVIDER_LABELS: Record<string, string> = {
  gemini: 'Gemini (Google) — LLM / Veo3',
  openai: 'OpenAI',
  minimax: 'MiniMax',
  glm: 'GLM / Zhipu (CogView · CogVideoX)',
  claude: 'Claude (Anthropic)',
  kling: 'Kling AI',
  runway: 'Runway',
}

/** Danh sách model theo {loại: {provider: [model]}}, lấy từ GET /settings/models. */
type ModelCatalog = Record<string, Record<string, string[]>>

// Backend là nguồn dữ liệu duy nhất. Hardcode ở đây từng khiến UI chào những
// model backend không hỗ trợ (Vidu, cogview-3-*) rồi âm thầm gen bằng model khác.
const EMPTY_CATALOG: ModelCatalog = { llm: {}, image: {}, video: {} }

type TestStatus = 'idle' | 'loading' | 'ok' | 'fail'

interface ApiSection {
  type: 'llm' | 'image' | 'video'
  label: string
  provider: string
  model: string
  apiKey: string
  keySet: boolean
}

export default function Settings() {
  const [catalog, setCatalog] = useState<ModelCatalog>(EMPTY_CATALOG)
  const [sections, setSections] = useState<ApiSection[]>([
    { type: 'llm', label: 'LLM — Gen kịch bản', provider: 'gemini', model: 'gemini-2.0-flash', apiKey: '', keySet: false },
    { type: 'image', label: 'Image AI — Gen hình ảnh', provider: 'gemini', model: 'imagen-3', apiKey: '', keySet: false },
    { type: 'video', label: 'Video AI — Gen video', provider: 'kling', model: 'kling-v2-master', apiKey: '', keySet: false },
  ])
  const [testStatus, setTestStatus] = useState<Record<string, TestStatus>>({})
  const [testMsg, setTestMsg] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/settings/models')
      .then(({ data }) => setCatalog({ ...EMPTY_CATALOG, ...data }))
      .catch(() => toast.error('Không tải được danh sách model từ server'))
  }, [])

  useEffect(() => {
    api.get('/settings/api-keys').then(({ data }) => {
      setSections((prev) => prev.map((s) => ({
        ...s,
        provider: data[`${s.type}_provider`] || s.provider,
        model: data[`${s.type}_model`] || s.model,
        keySet: data[`${s.type}_key_set`] || false,
      })))
    }).catch(() => {})
  }, [])

  /** Provider khả dụng của một loại = các key backend trả về cho loại đó. */
  const providersOf = (type: string): string[] => Object.keys(catalog[type] ?? {})
  const modelsOf = (type: string, provider: string): string[] => catalog[type]?.[provider] ?? []

  const updateSection = (type: string, field: string, value: string) => {
    setSections((prev) => prev.map((s) => {
      if (s.type !== type) return s
      const updated = { ...s, [field]: value }
      if (field === 'provider') {
        updated.model = modelsOf(type, value)[0] || ''
      }
      return updated
    }))
  }

  const handleTest = async (section: ApiSection) => {
    const key = section.type
    setTestStatus((prev) => ({ ...prev, [key]: 'loading' }))
    try {
      const { data } = await api.post('/settings/api-keys/test', {
        type: section.type,
        provider: section.provider,
        api_key: section.apiKey || '___saved___',
      })
      setTestStatus((prev) => ({ ...prev, [key]: data.ok ? 'ok' : 'fail' }))
      setTestMsg((prev) => ({ ...prev, [key]: data.message }))
    } catch {
      setTestStatus((prev) => ({ ...prev, [key]: 'fail' }))
      setTestMsg((prev) => ({ ...prev, [key]: 'Kết nối thất bại' }))
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload: Record<string, string> = {}
      sections.forEach((s) => {
        payload[`${s.type}_provider`] = s.provider
        payload[`${s.type}_model`] = s.model
        if (s.apiKey) payload[`${s.type}_key`] = s.apiKey
      })
      await api.put('/settings/api-keys', payload)
      toast.success('Đã lưu cài đặt API!')
      setSections((prev) => prev.map((s) => ({ ...s, apiKey: '', keySet: s.apiKey ? true : s.keySet })))
    } catch {
      toast.error('Lưu thất bại')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-container" style={{ maxWidth: 700 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Cài đặt API</h1>
          <p className="page-subtitle">Cắm API key của bạn để sử dụng các tính năng AI</p>
        </div>
        <button id="save-settings-btn" className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Đang lưu...' : 'Lưu cài đặt'}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {sections.map((section) => (
          <div key={section.type} className="card">
            <div className="card-header">
              <h3 className="card-title">{section.label}</h3>
              {section.keySet && <span className="badge badge-green">Key đã lưu</span>}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="label">Nhà cung cấp</label>
                  <select
                    className="select"
                    value={section.provider}
                    onChange={(e) => updateSection(section.type, 'provider', e.target.value)}
                  >
                    {providersOf(section.type).map((p) => (
                      <option key={p} value={p}>{PROVIDER_LABELS[p] || p}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="label">Model AI</label>
                  <select
                    className="select"
                    value={section.model}
                    onChange={(e) => updateSection(section.type, 'model', e.target.value)}
                  >
                    {modelsOf(section.type, section.provider).map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="label">
                  API Key {section.keySet ? '(để trống nếu không đổi)' : '*'}
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    id={`${section.type}-api-key`}
                    type="password"
                    className="input"
                    placeholder={section.keySet ? '••••••••••••••• (đã lưu)' : 'Nhập API key...'}
                    value={section.apiKey}
                    onChange={(e) => updateSection(section.type, 'apiKey', e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleTest(section)}
                    disabled={testStatus[section.type] === 'loading'}
                    title="Test kết nối"
                  >
                    {testStatus[section.type] === 'loading' ? (
                      <Loader size={14} style={{ animation: 'spin 0.6s linear infinite' }} />
                    ) : testStatus[section.type] === 'ok' ? (
                      <CheckCircle size={14} color="var(--success)" />
                    ) : testStatus[section.type] === 'fail' ? (
                      <XCircle size={14} color="var(--error)" />
                    ) : null}
                    Kiểm tra
                  </button>
                </div>
                {testMsg[section.type] && (
                  <p style={{
                    fontSize: 12, marginTop: 4,
                    color: testStatus[section.type] === 'ok' ? 'var(--success)' : 'var(--error)',
                  }}>
                    {testMsg[section.type]}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}

        <div style={{ padding: '12px 16px', background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--border)' }}>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            🔒 API key được <strong>mã hoá</strong> trước khi lưu vào database. Bạn là người duy nhất có thể dùng key của mình.
          </p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
            Gemini: <a href="https://aistudio.google.com" target="_blank" rel="noreferrer">aistudio.google.com</a>
            {' · '}OpenAI: <a href="https://platform.openai.com" target="_blank" rel="noreferrer">platform.openai.com</a>
            {' · '}MiniMax: <a href="https://platform.minimax.io" target="_blank" rel="noreferrer">platform.minimax.io</a>
            {' · '}GLM (Zhipu): <a href="https://open.bigmodel.cn" target="_blank" rel="noreferrer">open.bigmodel.cn</a>
            {' · '}Claude: <a href="https://console.anthropic.com" target="_blank" rel="noreferrer">console.anthropic.com</a>
            {' · '}Kling: <a href="https://klingai.com" target="_blank" rel="noreferrer">klingai.com</a>
          </p>
        </div>
      </div>
    </div>
  )
}
