import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, AlertTriangle } from 'lucide-react'
import api from '../../lib/api'
import toast from 'react-hot-toast'

interface Doc {
  id: string
  file_name: string
  file_type: string
  token_count: number
}

interface Props {
  projectId: string
  docs: Doc[]
  onDocsChange: (docs: Doc[]) => void
  selectedIds: string[]
  onSelectChange: (ids: string[]) => void
}

const TOKEN_LIMIT = 100000

export default function DocumentUpload({ projectId, docs, onDocsChange, selectedIds, onSelectChange }: Props) {
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true)
    for (const file of acceptedFiles) {
      try {
        const form = new FormData()
        form.append('file', file)
        const { data } = await api.post(`/projects/${projectId}/documents`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        onDocsChange([...docs, data])
        toast.success(`Đã tải lên: ${file.name}`)
      } catch (err: any) {
        toast.error(err.response?.data?.detail || `Lỗi tải ${file.name}`)
      }
    }
    setUploading(false)
  }, [projectId, docs, onDocsChange])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'], 'text/plain': ['.txt'], 'text/markdown': ['.md'] },
    multiple: true,
  })

  const removeDoc = async (id: string) => {
    try {
      await api.delete(`/projects/${projectId}/documents/${id}`)
      onDocsChange(docs.filter((d) => d.id !== id))
      onSelectChange(selectedIds.filter((sid) => sid !== id))
    } catch {
      toast.error('Xoá tài liệu thất bại')
    }
  }

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectChange(selectedIds.filter((sid) => sid !== id))
    } else {
      onSelectChange([...selectedIds, id])
    }
  }

  const totalTokens = docs.filter((d) => selectedIds.includes(d.id)).reduce((sum, d) => sum + (d.token_count || 0), 0)
  const overLimit = totalTokens > TOKEN_LIMIT

  return (
    <div>
      <div {...getRootProps()} className={`dropzone${isDragActive ? ' active' : ''}`}>
        <input {...getInputProps()} />
        <Upload size={20} style={{ margin: '0 auto 8px' }} />
        <p style={{ fontSize: 13 }}>
          {uploading ? 'Đang tải lên...' : isDragActive ? 'Thả file vào đây' : 'Kéo thả hoặc click để chọn file'}
        </p>
        <p style={{ fontSize: 12, marginTop: 4, color: 'var(--text-muted)' }}>PDF, DOCX, TXT, MD</p>
      </div>

      {docs.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {docs.map((doc) => (
            <div
              key={doc.id}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
                border: `1px solid ${selectedIds.includes(doc.id) ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 6, background: selectedIds.includes(doc.id) ? 'var(--accent-light)' : 'white',
                cursor: 'pointer', fontSize: 13,
              }}
              onClick={() => toggleSelect(doc.id)}
            >
              <input type="checkbox" checked={selectedIds.includes(doc.id)} onChange={() => {}} style={{ flexShrink: 0 }} />
              <FileText size={14} color="var(--text-secondary)" />
              <span className="truncate" style={{ flex: 1 }}>{doc.file_name}</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>~{doc.token_count?.toLocaleString()} tokens</span>
              <button
                className="btn btn-ghost btn-icon btn-sm"
                onClick={(e) => { e.stopPropagation(); removeDoc(doc.id) }}
                style={{ flexShrink: 0 }}
              >
                <X size={12} />
              </button>
            </div>
          ))}

          {selectedIds.length > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 12,
              color: overLimit ? 'var(--error)' : 'var(--text-muted)', marginTop: 4,
            }}>
              {overLimit && <AlertTriangle size={12} />}
              Đã chọn {selectedIds.length} tài liệu · ~{totalTokens.toLocaleString()} tokens
              {overLimit && ' — Vượt giới hạn! AI sẽ chỉ đọc phần đầu.'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
