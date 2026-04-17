'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { Calendar, FileText, FolderOpen, User, ArrowRight, Loader2, Briefcase } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import { api, type Candidate, type InterviewSession } from '@/lib/api'
import { loadOwnCandidate } from '@/lib/candidate-utils'
import { useAuth } from '@/contexts/auth-context'

export default function CandidateDashboardPage() {
  const { user } = useAuth()
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [interviews, setInterviews] = useState<InterviewSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const own = await loadOwnCandidate()
        setCandidate(own)
        if (own) {
          const list = await api.listInterviews(own.id)
          setInterviews(list)
        } else {
          setInterviews([])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить данные кандидата')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const activeInterviews = useMemo(
    () => interviews.filter((item) => item.status !== 'completed' && item.status !== 'cancelled'),
    [interviews],
  )

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем данные кандидата…
      </div>
    )
  }

  if (!candidate) {
    return (
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Профиль кандидата не создан</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Создайте профиль, заполните резюме и загрузите документы, чтобы HR увидел вашу карточку.
          </p>
          <Button asChild>
            <Link href="/candidate/profile">
              Перейти к профилю
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </NeonCardContent>
      </NeonCard>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Здравствуйте, {user?.name || candidate.full_name}</h1>
          <p className="text-sm text-muted-foreground">Отслеживайте статус найма и управляйте данными профиля.</p>
        </div>
        <StatusBadge status={candidate.status} />
      </div>

      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Профиль</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-2 text-sm">
            <p><span className="text-muted-foreground">ФИО:</span> {candidate.full_name}</p>
            <p><span className="text-muted-foreground">Эл. почта:</span> {candidate.email || 'Не указана'}</p>
            <p><span className="text-muted-foreground">Телефон:</span> {candidate.phone || 'Не указан'}</p>
            <Button variant="secondary" asChild className="w-full">
              <Link href="/candidate/profile">
                <User className="mr-2 h-4 w-4" />
                Редактировать профиль
              </Link>
            </Button>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Резюме</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-2 text-sm">
            <p>Навыков: {candidate.skills.length}</p>
            <p>Опыт: {candidate.experience.length}</p>
            <p>Образование: {candidate.education.length}</p>
            <Button variant="secondary" asChild className="w-full">
              <Link href="/candidate/resume">
                <FileText className="mr-2 h-4 w-4" />
                Открыть резюме
              </Link>
            </Button>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Собеседования</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-2 text-sm">
            <p>Всего: {interviews.length}</p>
            <p>Активных: {activeInterviews.length}</p>
            <Button variant="secondary" asChild className="w-full">
              <Link href="/candidate/interviews">
                <Calendar className="mr-2 h-4 w-4" />
                Перейти к интервью
              </Link>
            </Button>
          </NeonCardContent>
        </NeonCard>
      </div>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Быстрые действия</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Button variant="outline" asChild><Link href="/candidate/profile"><User className="mr-2 h-4 w-4" />Профиль</Link></Button>
          <Button variant="outline" asChild><Link href="/candidate/resume"><FileText className="mr-2 h-4 w-4" />Резюме</Link></Button>
          <Button variant="outline" asChild><Link href="/candidate/documents"><FolderOpen className="mr-2 h-4 w-4" />Документы</Link></Button>
          <Button variant="outline" asChild><Link href="/candidate/interviews"><Calendar className="mr-2 h-4 w-4" />Интервью</Link></Button>
          <Button variant="outline" asChild><Link href="/candidate/vacancies"><Briefcase className="mr-2 h-4 w-4" />Вакансии</Link></Button>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
