'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Calendar, CheckCircle2, FileText, Loader2, Play, Plus, Radio, Video, XCircle } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type Candidate, type InterviewReport, type InterviewRequestItem, type InterviewSession, type Vacancy } from '@/lib/api'

export default function HrInterviewsPage() {
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [requests, setRequests] = useState<InterviewRequestItem[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [reportMap, setReportMap] = useState<Record<string, InterviewReport>>({})

  const [createForm, setCreateForm] = useState({
    candidate_id: '',
    vacancy_id: '',
    interviewer_id: '',
    mode: 'mixed' as 'text' | 'voice' | 'mixed',
    scheduled_at: '',
    interview_format: 'online' as 'online' | 'offline' | 'phone',
    meeting_link: '',
    meeting_location: '',
    scheduling_comment: '',
  })

  const [reviewComment, setReviewComment] = useState<Record<string, string>>({})

  const [questionBankForm, setQuestionBankForm] = useState({
    vacancy_id: '',
    stage: 'theory' as 'intro' | 'theory' | 'ide',
    question_text: '',
    expected_difficulty: 3,
    metadata_json: '{"tags":["custom"]}',
  })

  const load = async () => {
    const [sessionList, requestList, candidateList, vacancyList] = await Promise.all([
      api.listInterviews(),
      api.listInterviewRequests(),
      api.listCandidates({ limit: 200 }),
      api.listVacancies(200),
    ])
    setSessions(sessionList)
    setRequests(requestList)
    setCandidates(candidateList.items)
    setVacancies(vacancyList)

    if (!createForm.candidate_id && candidateList.items.length) {
      setCreateForm((prev) => ({ ...prev, candidate_id: candidateList.items[0].id }))
    }
    if (!createForm.vacancy_id && vacancyList.length) {
      setCreateForm((prev) => ({ ...prev, vacancy_id: vacancyList[0].id }))
    }
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить интервью')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onCreate = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!createForm.candidate_id || !createForm.vacancy_id) {
      setError('Выберите кандидата и вакансию')
      return
    }

    try {
      await api.createInterview({
        candidate_id: createForm.candidate_id,
        vacancy_id: createForm.vacancy_id,
        interviewer_id: createForm.interviewer_id || undefined,
        mode: createForm.mode,
        scheduled_at: createForm.scheduled_at || null,
        interview_format: createForm.interview_format,
        meeting_link: createForm.meeting_link || undefined,
        meeting_location: createForm.meeting_location || undefined,
        scheduling_comment: createForm.scheduling_comment || undefined,
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать интервью')
    }
  }

  const onReviewRequest = async (requestItem: InterviewRequestItem, decision: 'approved' | 'rejected') => {
    setBusyId(requestItem.id)
    setError(null)
    try {
      await api.reviewInterviewRequest(requestItem.id, {
        decision,
        review_comment: reviewComment[requestItem.id] || undefined,
        vacancy_id: requestItem.vacancy_id || createForm.vacancy_id,
        mode: requestItem.requested_mode,
        scheduled_at: requestItem.requested_time || createForm.scheduled_at || undefined,
        interview_format: requestItem.requested_format,
        meeting_link: createForm.meeting_link || undefined,
        meeting_location: createForm.meeting_location || undefined,
        scheduling_comment: createForm.scheduling_comment || undefined,
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обработать запрос')
    } finally {
      setBusyId(null)
    }
  }

  const onStart = async (sessionId: string) => {
    setBusyId(sessionId)
    setError(null)
    try {
      await api.startInterview(sessionId)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить интервью')
    } finally {
      setBusyId(null)
    }
  }

  const onFinish = async (sessionId: string) => {
    setBusyId(sessionId)
    setError(null)
    try {
      await api.finishInterview(sessionId)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось завершить интервью')
    } finally {
      setBusyId(null)
    }
  }

  const onLoadReport = async (sessionId: string) => {
    setBusyId(sessionId)
    setError(null)
    try {
      const report = await api.getInterviewReport(sessionId)
      setReportMap((prev) => ({ ...prev, [sessionId]: report }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить отчет')
    } finally {
      setBusyId(null)
    }
  }

  const onCreateQuestionBankItem = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    try {
      await api.createInterviewQuestionBankItem({
        vacancy_id: questionBankForm.vacancy_id || undefined,
        stage: questionBankForm.stage,
        question_text: questionBankForm.question_text,
        expected_difficulty: questionBankForm.expected_difficulty,
        metadata_json: JSON.parse(questionBankForm.metadata_json || '{}'),
      })
      setQuestionBankForm((prev) => ({ ...prev, question_text: '', metadata_json: '{"tags":["custom"]}' }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить вопрос в банк')
    }
  }

  const candidateNameById = useMemo(() => {
    const map = new Map<string, string>()
    candidates.forEach((candidate) => map.set(candidate.id, candidate.full_name))
    return map
  }, [candidates])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем интервью…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Запросы собеседований от руководителей</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {!requests.length ? (
            <p className="text-sm text-muted-foreground">Новых запросов нет.</p>
          ) : (
            <div className="space-y-3">
              {requests.map((requestItem) => (
                <div key={requestItem.id} className="rounded-md border border-border/50 p-3">
                  <p className="text-sm font-medium">{candidateNameById.get(requestItem.candidate_id) || requestItem.candidate_id} · {requestItem.status}</p>
                  <p className="text-xs text-muted-foreground">{requestItem.requested_mode} / {requestItem.requested_format} · {requestItem.requested_time || 'без времени'}</p>
                  {requestItem.comment ? <p className="text-xs">{requestItem.comment}</p> : null}
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Input
                      placeholder="Комментарий HR"
                      value={reviewComment[requestItem.id] || ''}
                      onChange={(e) => setReviewComment((prev) => ({ ...prev, [requestItem.id]: e.target.value }))}
                      className="max-w-xs"
                    />
                    {requestItem.status === 'pending' ? (
                      <>
                        <Button size="sm" onClick={() => void onReviewRequest(requestItem, 'approved')} disabled={busyId === requestItem.id}>
                          <CheckCircle2 className="mr-2 h-4 w-4" />Подтвердить
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => void onReviewRequest(requestItem, 'rejected')} disabled={busyId === requestItem.id}>
                          <XCircle className="mr-2 h-4 w-4" />Отклонить
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Создать сессию AI-интервью</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onCreate} className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="candidate_id">Кандидат</Label>
              <select id="candidate_id" value={createForm.candidate_id} onChange={(e) => setCreateForm((p) => ({ ...p, candidate_id: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="">Выберите кандидата</option>
                {candidates.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="vacancy_id">Вакансия</Label>
              <select id="vacancy_id" value={createForm.vacancy_id} onChange={(e) => setCreateForm((p) => ({ ...p, vacancy_id: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="">Выберите вакансию</option>
                {vacancies.map((vacancy) => (
                  <option key={vacancy.id} value={vacancy.id}>{vacancy.title} ({vacancy.level})</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="interviewer_id">ID интервьюера (опционально)</Label>
              <Input id="interviewer_id" value={createForm.interviewer_id} onChange={(e) => setCreateForm((p) => ({ ...p, interviewer_id: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="mode">Режим</Label>
              <select id="mode" value={createForm.mode} onChange={(e) => setCreateForm((p) => ({ ...p, mode: e.target.value as 'text' | 'voice' | 'mixed' }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="text">Только текст</option>
                <option value="voice">Только голос</option>
                <option value="mixed">Смешанный режим</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="scheduled_at">Дата и время</Label>
              <Input id="scheduled_at" type="datetime-local" value={createForm.scheduled_at} onChange={(e) => setCreateForm((p) => ({ ...p, scheduled_at: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="interview_format">Формат интервью</Label>
              <select id="interview_format" value={createForm.interview_format} onChange={(e) => setCreateForm((p) => ({ ...p, interview_format: e.target.value as 'online' | 'offline' | 'phone' }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="online">online</option>
                <option value="offline">offline</option>
                <option value="phone">phone</option>
              </select>
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="meeting_link">Ссылка на встречу</Label>
              <Input id="meeting_link" value={createForm.meeting_link} onChange={(e) => setCreateForm((p) => ({ ...p, meeting_link: e.target.value }))} />
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="meeting_location">Место встречи</Label>
              <Input id="meeting_location" value={createForm.meeting_location} onChange={(e) => setCreateForm((p) => ({ ...p, meeting_location: e.target.value }))} />
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="scheduling_comment">Комментарий</Label>
              <Textarea id="scheduling_comment" rows={2} value={createForm.scheduling_comment} onChange={(e) => setCreateForm((p) => ({ ...p, scheduling_comment: e.target.value }))} />
            </div>
            <div className="md:col-span-2">
              <Button type="submit"><Plus className="mr-2 h-4 w-4" />Создать интервью</Button>
            </div>
          </form>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Онлайн-сессии и управление</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {!sessions.length ? (
            <p className="text-sm text-muted-foreground">Сессии пока не созданы.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div key={session.id} className="rounded-lg border border-border/60 bg-secondary/30 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">{session.title || `Интервью ${session.id.slice(0, 8)}`}</p>
                      <p className="text-xs text-muted-foreground">
                        Кандидат: {candidateNameById.get(session.candidate_id) || session.candidate_id} · Режим: {session.mode} · Статус: {session.status}
                      </p>
                      <p className="text-xs text-muted-foreground">Anti-cheat: {session.anti_cheat_level} ({session.anti_cheat_score.toFixed(1)}) · AI: {session.analysis_status}</p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {(session.status === 'draft' || session.status === 'scheduled') && (
                        <Button size="sm" onClick={() => void onStart(session.id)} disabled={busyId === session.id}>
                          {busyId === session.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                          Старт
                        </Button>
                      )}
                      {session.status !== 'completed' && session.status !== 'cancelled' && (
                        <Button size="sm" variant="outline" onClick={() => void onFinish(session.id)} disabled={busyId === session.id}>
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Завершить
                        </Button>
                      )}
                      <Button size="sm" variant="outline" onClick={() => void onLoadReport(session.id)} disabled={busyId === session.id}>
                        <FileText className="mr-2 h-4 w-4" />Отчет
                      </Button>
                      <Button size="sm" variant="outline" asChild>
                        <Link href={`/manager/evaluate/${session.id}`}>
                          <Calendar className="mr-2 h-4 w-4" />Оценка
                        </Link>
                      </Button>
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <Button size="sm" variant="ghost" asChild>
                      <Link href={`/candidate/interviews`}>
                        <Video className="mr-2 h-4 w-4" />Открыть интервью кандидата
                      </Link>
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => void api.getInterviewLiveState(session.id)}>
                      <Radio className="mr-2 h-4 w-4" />Проверить live-state
                    </Button>
                  </div>

                  {reportMap[session.id] ? (
                    <div className="mt-3 rounded-md border border-border/50 bg-background/70 p-3 text-xs">
                      <p className="font-semibold">Отчет AI: {reportMap[session.id].generation_status}</p>
                      <p>Суммарный score: {reportMap[session.id].score_total ?? '—'}</p>
                      <p>Рекомендации: {reportMap[session.id].recommendations_json?.length || 0}</p>
                      <p className="text-muted-foreground">{reportMap[session.id].summary_text || 'Резюме пока не готово.'}</p>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Банк вопросов для AI-интервью</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onCreateQuestionBankItem} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="qb_vacancy">Вакансия</Label>
                <select id="qb_vacancy" value={questionBankForm.vacancy_id} onChange={(e) => setQuestionBankForm((p) => ({ ...p, vacancy_id: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  <option value="">Общие вопросы</option>
                  {vacancies.map((vacancy) => (
                    <option key={vacancy.id} value={vacancy.id}>{vacancy.title}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="qb_stage">Этап</Label>
                <select id="qb_stage" value={questionBankForm.stage} onChange={(e) => setQuestionBankForm((p) => ({ ...p, stage: e.target.value as 'intro' | 'theory' | 'ide' }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  <option value="intro">Вводный</option>
                  <option value="theory">Теория</option>
                  <option value="ide">Практика IDE</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="qb_difficulty">Сложность</Label>
                <Input id="qb_difficulty" type="number" min={1} max={5} value={questionBankForm.expected_difficulty} onChange={(e) => setQuestionBankForm((p) => ({ ...p, expected_difficulty: Number(e.target.value || 3) }))} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="qb_question">Текст вопроса</Label>
              <Textarea id="qb_question" rows={3} value={questionBankForm.question_text} onChange={(e) => setQuestionBankForm((p) => ({ ...p, question_text: e.target.value }))} required />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="qb_metadata">JSON метаданных</Label>
              <Textarea id="qb_metadata" rows={2} value={questionBankForm.metadata_json} onChange={(e) => setQuestionBankForm((p) => ({ ...p, metadata_json: e.target.value }))} />
            </div>
            <Button type="submit">Добавить в банк</Button>
          </form>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
