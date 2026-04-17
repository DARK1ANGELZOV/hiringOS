'use client'

import Link from 'next/link'
import { FormEvent, useEffect, useState } from 'react'
import { Calendar, FileText, Loader2, Plus, ShieldAlert } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, type Candidate, type InterviewReport, type InterviewRequestItem, type InterviewSession, type Vacancy } from '@/lib/api'

export default function ManagerDashboardPage() {
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [requests, setRequests] = useState<InterviewRequestItem[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [reports, setReports] = useState<Record<string, InterviewReport>>({})
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [requestForm, setRequestForm] = useState({
    candidate_id: '',
    vacancy_id: '',
    requested_mode: 'mixed' as 'text' | 'voice' | 'mixed',
    requested_format: 'online' as 'online' | 'offline' | 'phone',
    requested_time: '',
    comment: '',
  })

  const load = async () => {
    const [sessionList, candidateList, vacancyList, requestList] = await Promise.all([
      api.listInterviews(),
      api.listCandidates({ limit: 200 }),
      api.listVacancies(200),
      api.listInterviewRequests(),
    ])
    setSessions(sessionList)
    setCandidates(candidateList.items)
    setVacancies(vacancyList)
    setRequests(requestList)

    if (!requestForm.candidate_id && candidateList.items.length) {
      setRequestForm((prev) => ({ ...prev, candidate_id: candidateList.items[0].id }))
    }
    if (!requestForm.vacancy_id && vacancyList.length) {
      setRequestForm((prev) => ({ ...prev, vacancy_id: vacancyList[0].id }))
    }
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить дашборд руководителя')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const candidateName = (candidateId: string) => candidates.find((candidate) => candidate.id === candidateId)?.full_name || candidateId

  const loadReport = async (sessionId: string) => {
    setError(null)
    try {
      const report = await api.getInterviewReport(sessionId)
      setReports((prev) => ({ ...prev, [sessionId]: report }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить отчет')
    }
  }

  const onCreateRequest = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)

    try {
      await api.createInterviewRequest({
        candidate_id: requestForm.candidate_id,
        vacancy_id: requestForm.vacancy_id || undefined,
        requested_mode: requestForm.requested_mode,
        requested_format: requestForm.requested_format,
        requested_time: requestForm.requested_time || undefined,
        comment: requestForm.comment || undefined,
      })
      await load()
      setRequestForm((prev) => ({ ...prev, comment: '' }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отправить запрос на интервью')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем дашборд руководителя…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Дашборд руководителя</h1>
        <p className="text-sm text-muted-foreground">Оценка кандидатов после интервью, запрос интервью у HR и просмотр AI-отчетов.</p>
      </div>

      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Запросить интервью у HR</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onCreateRequest} className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="candidate_id">Кандидат</Label>
              <select id="candidate_id" value={requestForm.candidate_id} onChange={(e) => setRequestForm((p) => ({ ...p, candidate_id: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                {candidates.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="vacancy_id">Вакансия</Label>
              <select id="vacancy_id" value={requestForm.vacancy_id} onChange={(e) => setRequestForm((p) => ({ ...p, vacancy_id: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                {vacancies.map((vacancy) => (
                  <option key={vacancy.id} value={vacancy.id}>{vacancy.title}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="requested_mode">Режим</Label>
              <select id="requested_mode" value={requestForm.requested_mode} onChange={(e) => setRequestForm((p) => ({ ...p, requested_mode: e.target.value as 'text' | 'voice' | 'mixed' }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="text">text</option>
                <option value="voice">voice</option>
                <option value="mixed">mixed</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="requested_format">Формат</Label>
              <select id="requested_format" value={requestForm.requested_format} onChange={(e) => setRequestForm((p) => ({ ...p, requested_format: e.target.value as 'online' | 'offline' | 'phone' }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="online">online</option>
                <option value="offline">offline</option>
                <option value="phone">phone</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="requested_time">Желаемое время</Label>
              <Input id="requested_time" type="datetime-local" value={requestForm.requested_time} onChange={(e) => setRequestForm((p) => ({ ...p, requested_time: e.target.value }))} />
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="request_comment">Комментарий</Label>
              <Input id="request_comment" value={requestForm.comment} onChange={(e) => setRequestForm((p) => ({ ...p, comment: e.target.value }))} />
            </div>
            <div className="md:col-span-2">
              <Button type="submit" disabled={busy}><Plus className="mr-2 h-4 w-4" />Отправить запрос</Button>
            </div>
          </form>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Мои запросы интервью</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          {!requests.length ? (
            <p className="text-sm text-muted-foreground">Запросы пока отсутствуют.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {requests.map((requestItem) => (
                <div key={requestItem.id} className="rounded-md border border-border/50 p-2">
                  <p className="font-medium">{candidateName(requestItem.candidate_id)} · {requestItem.status}</p>
                  <p className="text-xs text-muted-foreground">{requestItem.requested_mode} / {requestItem.requested_format} · {requestItem.requested_time || 'без времени'}</p>
                  {requestItem.comment ? <p className="text-xs">{requestItem.comment}</p> : null}
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Сессии для оценки</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          {!sessions.length ? (
            <p className="text-sm text-muted-foreground">Интервью пока нет.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div key={session.id} className="rounded-lg border border-border/60 bg-secondary/30 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{session.title || `Интервью ${session.id.slice(0, 8)}`}</p>
                      <p className="text-xs text-muted-foreground">
                        Кандидат: {candidateName(session.candidate_id)} · Статус: {session.status} · AI: {session.analysis_status}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Anti-cheat: {session.anti_cheat_level} ({session.anti_cheat_score.toFixed(1)})
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => void loadReport(session.id)}>
                        <FileText className="mr-2 h-4 w-4" />Отчет
                      </Button>
                      <Button size="sm" asChild>
                        <Link href={`/manager/evaluate/${session.id}`}>
                          <Calendar className="mr-2 h-4 w-4" />Оценить
                        </Link>
                      </Button>
                    </div>
                  </div>

                  {reports[session.id] ? (
                    <div className="mt-3 space-y-1 rounded-md border border-border/50 bg-background/70 p-3 text-xs">
                      <p><span className="font-semibold">Статус отчета:</span> {reports[session.id].generation_status}</p>
                      <p><span className="font-semibold">Итоговый балл:</span> {reports[session.id].score_total ?? '—'}</p>
                      <p><span className="font-semibold">Коммуникация:</span> {reports[session.id].score_communication ?? '—'}</p>
                      <p><span className="font-semibold">Решение задач:</span> {reports[session.id].score_problem_solving ?? '—'}</p>
                      <p className="text-muted-foreground">{reports[session.id].summary_text || 'Сводка еще не готова.'}</p>
                      {!!reports[session.id].risk_flags_json?.length && (
                        <p className="flex items-center gap-1 text-amber-300">
                          <ShieldAlert className="h-3.5 w-3.5" />
                          Риск-флаги: {reports[session.id].risk_flags_json.length}
                        </p>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
