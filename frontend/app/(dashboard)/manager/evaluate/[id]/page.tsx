'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Loader2, Save } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type InterviewReport, type InterviewSession } from '@/lib/api'

type SignalView = { id: string; signal_type: string; severity: string }

export default function ManagerEvaluatePage() {
  const params = useParams<{ id: string }>()
  const sessionId = params.id

  const [session, setSession] = useState<InterviewSession | null>(null)
  const [report, setReport] = useState<InterviewReport | null>(null)
  const [signals, setSignals] = useState<{ risk_level: string; anti_cheat_score: number; items: SignalView[] } | null>(null)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [form, setForm] = useState({
    overall_rating: 4,
    strengths: '',
    weaknesses: '',
    recommendation: 'continue',
    comments: '',
  })

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const [sessionData, reportData, signalData] = await Promise.all([
          api.getInterview(sessionId),
          api.getInterviewReport(sessionId),
          api.getInterviewSignals(sessionId),
        ])

        setSession(sessionData)
        setReport(reportData)
        setSignals({
          risk_level: signalData.risk_level,
          anti_cheat_score: signalData.anti_cheat_score,
          items: signalData.items.map((item) => ({
            id: item.id,
            signal_type: item.signal_type,
            severity: item.severity,
          })),
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить данные оценки')
      } finally {
        setLoading(false)
      }
    })()
  }, [sessionId])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      await api.createFeedback({
        session_id: sessionId,
        overall_rating: form.overall_rating,
        strengths: form.strengths,
        weaknesses: form.weaknesses,
        recommendation: form.recommendation,
        comments: form.comments,
      })
      setSuccess('Оценка успешно сохранена')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить оценку')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем данные интервью…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Оценка кандидата после интервью</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-3 text-sm">
          {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-red-300">{error}</div> : null}
          {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-emerald-300">{success}</div> : null}

          <p><span className="font-semibold">ID сессии:</span> {session?.id}</p>
          <p><span className="font-semibold">Статус:</span> {session?.status}</p>
          <p><span className="font-semibold">Статус AI-отчета:</span> {report?.generation_status || '—'}</p>
          <p><span className="font-semibold">Общий балл:</span> {report?.score_total ?? '—'}</p>
          <p>
            <span className="font-semibold">Anti-cheat риск:</span> {signals?.risk_level || '—'} ({signals?.anti_cheat_score?.toFixed(1) ?? '—'})
          </p>
          <p className="text-muted-foreground">{report?.summary_text || 'Сводка AI пока отсутствует.'}</p>

          {!!signals?.items?.length && (
            <div className="rounded-md border border-border/50 bg-background/70 p-2 text-xs">
              <p className="mb-1 font-semibold">Сигналы anti-cheat:</p>
              <ul className="space-y-0.5">
                {signals.items.slice(0, 10).map((item) => (
                  <li key={item.id}>{item.signal_type} · {item.severity}</li>
                ))}
              </ul>
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Форма обратной связи руководителя</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onSubmit} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="overall_rating">Общая оценка (1-5)</Label>
              <input
                id="overall_rating"
                type="number"
                min={1}
                max={5}
                value={form.overall_rating}
                onChange={(e) => setForm((prev) => ({ ...prev, overall_rating: Number(e.target.value || 1) }))}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="strengths">Сильные стороны</Label>
              <Textarea
                id="strengths"
                rows={4}
                value={form.strengths}
                onChange={(e) => setForm((prev) => ({ ...prev, strengths: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="weaknesses">Слабые стороны</Label>
              <Textarea
                id="weaknesses"
                rows={4}
                value={form.weaknesses}
                onChange={(e) => setForm((prev) => ({ ...prev, weaknesses: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="recommendation">Рекомендация</Label>
              <select
                id="recommendation"
                value={form.recommendation}
                onChange={(e) => setForm((prev) => ({ ...prev, recommendation: e.target.value }))}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="continue">Продолжить</option>
                <option value="rejected">Отказать</option>
                <option value="reserve">Резерв</option>
                <option value="offer">Сделать оффер</option>
                <option value="repeat_interview">Повторное интервью</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="comments">Комментарий</Label>
              <Textarea
                id="comments"
                rows={4}
                value={form.comments}
                onChange={(e) => setForm((prev) => ({ ...prev, comments: e.target.value }))}
              />
            </div>

            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Сохранить отзыв
            </Button>
          </form>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
