'use client'

import { ChangeEvent, useEffect, useRef, useState } from 'react'
import { Download, File, Loader2, Trash2, Upload } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { api, type Candidate, type DocumentItem } from '@/lib/api'
import { loadOwnCandidate } from '@/lib/candidate-utils'

const documentTypeOptions = [
  { value: 'resume', label: 'Резюме' },
  { value: 'cover_letter', label: 'Сопроводительное письмо' },
  { value: 'certificate', label: 'Сертификат' },
  { value: 'diploma', label: 'Диплом' },
  { value: 'photo', label: 'Фото' },
  { value: 'attachment', label: 'Вложение' },
  { value: 'other', label: 'Другое' },
]

export default function CandidateDocumentsPage() {
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [items, setItems] = useState<DocumentItem[]>([])
  const [documentType, setDocumentType] = useState('resume')
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const replaceInputRef = useRef<HTMLInputElement | null>(null)
  const [replaceTargetId, setReplaceTargetId] = useState<string | null>(null)

  const load = async () => {
    const own = await loadOwnCandidate()
    setCandidate(own)
    if (!own) {
      setItems([])
      return
    }
    const docs = await api.listDocuments(own.id)
    setItems(docs)
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить документы')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const onUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !candidate) return

    setUploading(true)
    setError(null)
    try {
      await api.uploadDocument(candidate.id, documentType, file)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить документ')
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const onDownload = async (documentId: string) => {
    setBusyDocumentId(documentId)
    setError(null)
    try {
      const payload = await api.getDocumentDownloadUrl(documentId)
      window.open(payload.download_url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось скачать документ')
    } finally {
      setBusyDocumentId(null)
    }
  }

  const onDelete = async (documentId: string) => {
    setBusyDocumentId(documentId)
    setError(null)
    try {
      await api.deleteDocument(documentId)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить документ')
    } finally {
      setBusyDocumentId(null)
    }
  }

  const onPickReplace = (documentId: string) => {
    setReplaceTargetId(documentId)
    replaceInputRef.current?.click()
  }

  const onReplaceSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !replaceTargetId) return

    setBusyDocumentId(replaceTargetId)
    setError(null)
    try {
      await api.replaceDocument(replaceTargetId, file)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось заменить документ')
    } finally {
      setBusyDocumentId(null)
      setReplaceTargetId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем документы…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <input ref={replaceInputRef} type="file" className="hidden" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={onReplaceSelected} />

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Загрузка документов</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-4">
          {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

          {!candidate ? (
            <p className="text-sm text-muted-foreground">Сначала создайте профиль кандидата.</p>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-[220px,1fr] md:items-end">
                <div className="space-y-1.5">
                  <Label htmlFor="document_type">Тип документа</Label>
                  <select
                    id="document_type"
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                  >
                    {documentTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="document_file">Файл (PDF/DOC/DOCX/JPG/PNG)</Label>
                  <input id="document_file" type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={onUpload} disabled={uploading} />
                </div>
              </div>

              {uploading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Загружаем файл…
                </div>
              ) : (
                <Button variant="outline" asChild>
                  <label htmlFor="document_file" className="cursor-pointer">
                    <Upload className="mr-2 h-4 w-4" />
                    Выбрать и загрузить
                  </label>
                </Button>
              )}
            </>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Загруженные документы</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {!items.length ? (
            <p className="text-sm text-muted-foreground">Документы пока не загружены.</p>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div key={item.id} className="rounded-md border border-border/60 bg-secondary/30 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{item.original_filename}</p>
                      <p className="text-xs text-muted-foreground">
                        Тип: {item.document_type} · {Math.round(item.size_bytes / 1024)} KB · {new Date(item.created_at).toLocaleString('ru-RU')}
                      </p>
                    </div>
                    <File className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => void onDownload(item.id)} disabled={busyDocumentId === item.id}>
                      <Download className="mr-2 h-4 w-4" />Скачать
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => onPickReplace(item.id)} disabled={busyDocumentId === item.id}>
                      <Upload className="mr-2 h-4 w-4" />Заменить
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => void onDelete(item.id)} disabled={busyDocumentId === item.id}>
                      <Trash2 className="mr-2 h-4 w-4" />Удалить
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
