'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Calendar, Loader2, Play, FileText, ShieldAlert } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { api, type Candidate, type InterviewSession } from '@/lib/api'
import { loadOwnCandidate } from '@/lib/candidate-utils'

export default function CandidateInterviewsPage() {
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [loading, setLoading] = useState(true)
  const [actionBusyId, setActionBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [speechDiagnostics, setSpeechDiagnostics] = useState<{ stt_loaded: boolean; stt_error: string | null; tts_loaded: boolean; tts_error: string | null } | null>(null)

  const load = async () => {
    const own = await loadOwnCandidate()
    setCandidate(own)
    if (!own) {
      setSessions([])
      return
    }

    const list = await api.listInterviews(own.id)
    setSessions(list)
    try {
      const diagnostics = await api.getSpeechDiagnostics()
      setSpeechDiagnostics(diagnostics)
    } catch {
      setSpeechDiagnostics(null)
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
  }, [])

  const startSession = async (sessionId: string) => {
    setActionBusyId(sessionId)
    setError(null)
    try {
      await api.startInterview(sessionId)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось начать интервью')
    } finally {
      setActionBusyId(null)
    }
  }

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
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Мои собеседования</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {error ? <div className="mb-4 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
          {!candidate ? (
            <p className="text-sm text-muted-foreground">Профиль кандидата не найден. Создайте профиль на странице «Профиль».</p>
          ) : !sessions.length ? (
            <p className="text-sm text-muted-foreground">Собеседования пока не назначены.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div key={session.id} className="rounded-lg border border-border/60 bg-secondary/30 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">{session.title || `Интервью ${session.id.slice(0, 8)}`}</p>
                      <p className="text-xs text-muted-foreground">
                        Режим: {session.mode} · Статус: {session.status} · Аналитика: {session.analysis_status}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Риск anti-cheat: {session.anti_cheat_level} ({session.anti_cheat_score.toFixed(1)})
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {(session.status === 'draft' || session.status === 'scheduled') && (
                        <Button size="sm" onClick={() => void startSession(session.id)} disabled={actionBusyId === session.id}>
                          {actionBusyId === session.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                          Начать
                        </Button>
                      )}
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/hr/interviews?session=${session.id}`}>
                          <Calendar className="mr-2 h-4 w-4" />
                          Открыть
                        </Link>
                      </Button>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/manager/evaluate/${session.id}`}>
                          <FileText className="mr-2 h-4 w-4" />
                          Отчет
                        </Link>
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Как работает anti-cheat</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-2 text-sm text-muted-foreground">
          <p className="flex items-start gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 text-amber-300" />Система фиксирует только сигналы риска и не блокирует вас автоматически.</p>
          <p className="flex items-start gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 text-amber-300" />Все решения по кандидату принимает HR/руководитель после просмотра отчета.</p>
          {speechDiagnostics ? (
            <div className="rounded-md border border-border/50 bg-secondary/30 p-2 text-xs">
              <p>STT: {speechDiagnostics.stt_loaded ? 'доступен' : `недоступен (${speechDiagnostics.stt_error || 'error'})`}</p>
              <p>TTS: {speechDiagnostics.tts_loaded ? 'доступен' : `недоступен (${speechDiagnostics.tts_error || 'error'})`}</p>
            </div>
          ) : null}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
