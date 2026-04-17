'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { Calendar, Loader2, Users, Briefcase, ArrowRight } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { api, type Candidate, type InterviewSession } from '@/lib/api'
import { statusLabel } from '@/lib/status'

export default function HrDashboardPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [interviews, setInterviews] = useState<InterviewSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const [candidateList, interviewList] = await Promise.all([
          api.listCandidates({ limit: 200 }),
          api.listInterviews(),
        ])
        setCandidates(candidateList.items)
        setInterviews(interviewList)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить дашборд HR')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const statusStats = useMemo(() => {
    return candidates.reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = (acc[item.status] || 0) + 1
      return acc
    }, {})
  }, [candidates])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем HR-дашборд…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">HR-дашборд</h1>
          <p className="text-sm text-muted-foreground">Единая точка управления кандидатами, интервью и статусами найма.</p>
        </div>
        <Button asChild>
          <Link href="/hr/candidates">
            Открыть базу кандидатов
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>

      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Кандидаты</NeonCardTitle></NeonCardHeader>
          <NeonCardContent>
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-primary" />
              <span className="text-3xl font-bold">{candidates.length}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Всего в базе</p>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Интервью</NeonCardTitle></NeonCardHeader>
          <NeonCardContent>
            <div className="flex items-center gap-3">
              <Calendar className="h-5 w-5 text-primary" />
              <span className="text-3xl font-bold">{interviews.length}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Созданных сессий</p>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Активные</NeonCardTitle></NeonCardHeader>
          <NeonCardContent>
            <div className="flex items-center gap-3">
              <Briefcase className="h-5 w-5 text-primary" />
              <span className="text-3xl font-bold">{interviews.filter((i) => i.status === 'in_progress').length}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Интервью в процессе</p>
          </NeonCardContent>
        </NeonCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Статусы кандидатов</NeonCardTitle></NeonCardHeader>
          <NeonCardContent>
            <div className="space-y-2 text-sm">
              {Object.entries(statusStats).length ? (
                Object.entries(statusStats)
                  .sort((a, b) => b[1] - a[1])
                  .map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between rounded-md border border-border/50 p-2">
                      <span>{statusLabel(status)}</span>
                      <span className="font-semibold">{count}</span>
                    </div>
                  ))
              ) : (
                <p className="text-muted-foreground">Пока нет данных по статусам.</p>
              )}
            </div>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Быстрые переходы</NeonCardTitle></NeonCardHeader>
          <NeonCardContent className="grid gap-2">
            <Button variant="outline" asChild><Link href="/hr/candidates">Кандидаты и фильтры</Link></Button>
            <Button variant="outline" asChild><Link href="/hr/interviews">Календарь интервью</Link></Button>
            <Button variant="outline" asChild><Link href="/screening">Тесты и скрининг</Link></Button>
            <Button variant="outline" asChild><Link href="/admin">Аудит и отчеты</Link></Button>
          </NeonCardContent>
        </NeonCard>
      </div>
    </div>
  )
}
