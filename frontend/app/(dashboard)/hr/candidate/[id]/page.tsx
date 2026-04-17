'use client'

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Calendar, Download, Loader2, Save, Trash2, Upload } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type Candidate, type CandidateStatusHistoryItem, type DocumentItem, type InterviewSession, type VacancyApplication } from '@/lib/api'
import { statusLabel } from '@/lib/status'

const STATUSES = ['new', 'screening', 'hr_interview', 'tech_interview', 'manager_review', 'interview_done', 'decision_pending', 'reserve', 'offer', 'hired', 'rejected']

export default function HrCandidateDetailPage() {
  const params = useParams<{ id: string }>()
  const candidateId = params.id

  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [interviews, setInterviews] = useState<InterviewSession[]>([])
  const [applications, setApplications] = useState<VacancyApplication[]>([])
  const [statusHistory, setStatusHistory] = useState<CandidateStatusHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const replaceInputRef = useRef<HTMLInputElement | null>(null)
  const [replaceTargetId, setReplaceTargetId] = useState<string | null>(null)

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    city: '',
    location: '',
    desired_position: '',
    headline: '',
    summary: '',
    status: 'new',
    status_comment: '',
  })

  const load = async () => {
    const [candidateData, docs, sessions, history, applicationRows] = await Promise.all([
      api.getCandidate(candidateId),
      api.listDocuments(candidateId),
      api.listInterviews(candidateId),
      api.listCandidateStatusHistory(candidateId),
      api.listVacancyApplications({ candidate_id: candidateId }),
    ])

    setCandidate(candidateData)
    setDocuments(docs)
    setInterviews(sessions)
    setStatusHistory(history)
    setApplications(applicationRows)
    setForm({
      full_name: candidateData.full_name,
      email: candidateData.email || '',
      phone: candidateData.phone || '',
      city: candidateData.city || '',
      location: candidateData.location || '',
      desired_position: candidateData.desired_position || '',
      headline: candidateData.headline || '',
      summary: candidateData.summary || '',
      status: candidateData.status,
      status_comment: '',
    })
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить карточку кандидата')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId])

  const onSave = async (event: FormEvent) => {
    event.preventDefault()
    if (!candidate) return

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      await api.updateCandidate(candidate.id, {
        full_name: form.full_name,
        email: form.email || null,
        phone: form.phone || null,
        city: form.city || null,
        location: form.location || null,
        desired_position: form.desired_position || null,
        headline: form.headline || null,
        summary: form.summary || null,
      })

      if (form.status !== candidate.status) {
        await api.updateCandidateStatus(candidate.id, {
          new_status: form.status,
          comment: form.status_comment || undefined,
        })
      }

      await load()
      setSuccess('Карточка кандидата сохранена')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить карточку кандидата')
    } finally {
      setSaving(false)
    }
  }

  const onDownloadDocument = async (documentId: string) => {
    setBusyDocumentId(documentId)
    setError(null)
    try {
      const payload = await api.getDocumentDownloadUrl(documentId)
      window.open(payload.download_url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось получить ссылку скачивания')
    } finally {
      setBusyDocumentId(null)
    }
  }

  const onDeleteDocument = async (documentId: string) => {
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

  const onPickReplaceDocument = (documentId: string) => {
    setReplaceTargetId(documentId)
    replaceInputRef.current?.click()
  }

  const onReplaceDocumentSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    if (!replaceTargetId) return
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

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

  const candidateName = useMemo(() => candidate?.full_name || 'Кандидат', [candidate])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем карточку кандидата…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <input ref={replaceInputRef} type="file" className="hidden" onChange={onReplaceDocumentSelected} />

      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Карточка кандидата</h1>
        <Button variant="outline" asChild>
          <Link href="/hr/candidates">Назад к списку</Link>
        </Button>
      </div>

      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
      {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{success}</div> : null}

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>{candidateName}</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onSave} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="full_name">ФИО</Label>
                <Input id="full_name" value={form.full_name} onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="desired_position">Желаемая должность</Label>
                <Input id="desired_position" value={form.desired_position} onChange={(e) => setForm((prev) => ({ ...prev, desired_position: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Эл. почта</Label>
                <Input id="email" value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="phone">Телефон</Label>
                <Input id="phone" value={form.phone} onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="city">Город</Label>
                <Input id="city" value={form.city} onChange={(e) => setForm((prev) => ({ ...prev, city: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="location">Локация</Label>
                <Input id="location" value={form.location} onChange={(e) => setForm((prev) => ({ ...prev, location: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="status">Статус</Label>
                <select
                  id="status"
                  value={form.status}
                  onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {STATUSES.map((statusItem) => (
                    <option key={statusItem} value={statusItem}>
                      {statusLabel(statusItem)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="headline">Заголовок</Label>
                <Input id="headline" value={form.headline} onChange={(e) => setForm((prev) => ({ ...prev, headline: e.target.value }))} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="status_comment">Комментарий к смене статуса</Label>
              <Input id="status_comment" value={form.status_comment} onChange={(e) => setForm((prev) => ({ ...prev, status_comment: e.target.value }))} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="summary">Комментарий HR</Label>
              <Textarea id="summary" rows={4} value={form.summary} onChange={(e) => setForm((prev) => ({ ...prev, summary: e.target.value }))} />
            </div>

            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Сохранить
            </Button>
          </form>
        </NeonCardContent>
      </NeonCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Документы</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            {!documents.length ? (
              <p className="text-sm text-muted-foreground">Документы отсутствуют.</p>
            ) : (
              <div className="space-y-2 text-sm">
                {documents.map((item) => (
                  <div key={item.id} className="rounded-md border border-border/50 p-3">
                    <p className="font-medium">{item.original_filename}</p>
                    <p className="mb-2 text-xs text-muted-foreground">{item.document_type} · {Math.round(item.size_bytes / 1024)} KB</p>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => void onDownloadDocument(item.id)} disabled={busyDocumentId === item.id}>
                        <Download className="mr-2 h-4 w-4" />Скачать
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => onPickReplaceDocument(item.id)} disabled={busyDocumentId === item.id}>
                        <Upload className="mr-2 h-4 w-4" />Заменить
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDeleteDocument(item.id)} disabled={busyDocumentId === item.id}>
                        <Trash2 className="mr-2 h-4 w-4" />Удалить
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Собеседования</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            {!interviews.length ? (
              <p className="text-sm text-muted-foreground">Сессии интервью не назначены.</p>
            ) : (
              <div className="space-y-2">
                {interviews.map((session) => (
                  <div key={session.id} className="flex items-center justify-between rounded-md border border-border/50 p-2">
                    <div>
                      <p className="text-sm font-medium">{session.title || `Интервью ${session.id.slice(0, 8)}`}</p>
                      <p className="text-xs text-muted-foreground">{session.mode} · {session.status}</p>
                    </div>
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/hr/interviews?session=${session.id}`}>
                        <Calendar className="mr-2 h-4 w-4" />
                        Открыть
                      </Link>
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </NeonCardContent>
        </NeonCard>
      </div>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Отклики на вакансии</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {!applications.length ? (
            <p className="text-sm text-muted-foreground">Отклики пока отсутствуют.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {applications.map((item) => (
                <div key={item.id} className="rounded-md border border-border/50 p-2">
                  <p className="font-medium">Вакансия: {item.vacancy_id}</p>
                  <p className="text-xs text-muted-foreground">Статус: {item.status} · {new Date(item.created_at).toLocaleString('ru-RU')}</p>
                  {item.note ? <p className="text-xs">Комментарий: {item.note}</p> : null}
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>История смены статусов</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {!statusHistory.length ? (
            <p className="text-sm text-muted-foreground">История статусов пока пуста.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {statusHistory.map((item) => (
                <div key={item.id} className="rounded-md border border-border/50 p-2">
                  <p className="font-medium">
                    {statusLabel(item.previous_status || 'new')} → {statusLabel(item.new_status)}
                  </p>
                  <p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString('ru-RU')}</p>
                  {item.comment ? <p className="text-xs">Комментарий: {item.comment}</p> : null}
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
