'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Briefcase, Loader2, Send } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type Candidate, type Vacancy, type VacancyApplication } from '@/lib/api'
import { loadOwnCandidate } from '@/lib/candidate-utils'

export default function CandidateVacanciesPage() {
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [applications, setApplications] = useState<VacancyApplication[]>([])
  const [drafts, setDrafts] = useState<Record<string, { cover: string; note: string }>>({})
  const [loading, setLoading] = useState(true)
  const [busyVacancyId, setBusyVacancyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const applicationsByVacancy = useMemo(() => {
    const mapped: Record<string, VacancyApplication> = {}
    for (const item of applications) mapped[item.vacancy_id] = item
    return mapped
  }, [applications])

  const load = async () => {
    const own = await loadOwnCandidate()
    setCandidate(own)
    if (!own) {
      setVacancies([])
      setApplications([])
      return
    }
    const [vacancyRows, applicationRows] = await Promise.all([
      api.listVacanciesForCandidate(own.id),
      api.listMyVacancyApplications(),
    ])
    setVacancies(vacancyRows)
    setApplications(applicationRows)
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить вакансии')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const onApply = async (event: FormEvent, vacancyId: string) => {
    event.preventDefault()
    setBusyVacancyId(vacancyId)
    setError(null)
    setSuccess(null)
    try {
      const draft = drafts[vacancyId]
      await api.applyToVacancy(vacancyId, {
        cover_letter_text: draft?.cover || undefined,
        note: draft?.note || undefined,
      })
      await load()
      setSuccess('Отклик отправлен')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отправить отклик')
    } finally {
      setBusyVacancyId(null)
    }
  }

  const onWithdraw = async (application: VacancyApplication) => {
    setBusyVacancyId(application.vacancy_id)
    setError(null)
    setSuccess(null)
    try {
      await api.updateVacancyApplicationStatus(application.id, { status: 'withdrawn' })
      await load()
      setSuccess('Отклик отозван')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отозвать отклик')
    } finally {
      setBusyVacancyId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем вакансии…
      </div>
    )
  }

  if (!candidate) {
    return (
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Сначала создайте профиль кандидата</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="text-sm text-muted-foreground">
          После создания профиля откроется возможность откликаться на вакансии.
        </NeonCardContent>
      </NeonCard>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Вакансии</h1>
        <p className="text-sm text-muted-foreground">Подберите подходящую вакансию и отправьте отклик в один шаг.</p>
      </div>

      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
      {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{success}</div> : null}

      {!vacancies.length ? (
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Пока нет открытых вакансий</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="text-sm text-muted-foreground">
            HR и руководители смогут добавить вакансии, после чего они появятся здесь.
          </NeonCardContent>
        </NeonCard>
      ) : (
        <div className="space-y-4">
          {vacancies.map((vacancy) => {
            const application = applicationsByVacancy[vacancy.id]
            const isApplied = Boolean(application && application.status !== 'withdrawn')
            const draft = drafts[vacancy.id] || { cover: '', note: '' }

            return (
              <NeonCard key={vacancy.id}>
                <NeonCardHeader>
                  <NeonCardTitle className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4" />
                    {vacancy.title}
                  </NeonCardTitle>
                </NeonCardHeader>
                <NeonCardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Уровень: {vacancy.level} {vacancy.department ? `· Отдел: ${vacancy.department}` : ''}
                  </p>
                  {vacancy.description ? <p className="text-sm">{vacancy.description}</p> : null}
                  {!!vacancy.stack_json?.length ? (
                    <div className="flex flex-wrap gap-2">
                      {vacancy.stack_json.map((item) => (
                        <span key={item} className="rounded-full border border-border/70 px-2 py-0.5 text-xs">
                          {item}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  {vacancy.match ? (
                    <div className="rounded-md border border-border/60 bg-secondary/30 p-3 text-sm">
                      <p className="font-medium">AI Match: {vacancy.match.score_percent.toFixed(1)}%</p>
                      <p className="text-xs text-muted-foreground">Совпало: {vacancy.match.matched_skills.join(', ') || '—'}</p>
                      <p className="text-xs text-muted-foreground">Не хватает: {vacancy.match.missing_skills.join(', ') || '—'}</p>
                    </div>
                  ) : null}

                  {isApplied ? (
                    <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
                      <p>
                        Вы уже откликнулись. Статус: <span className="font-medium">{application.status}</span>
                      </p>
                      <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => void onWithdraw(application)} disabled={busyVacancyId === vacancy.id}>
                        Отозвать отклик
                      </Button>
                    </div>
                  ) : (
                    <form className="space-y-2 rounded-md border border-border/60 p-3" onSubmit={(event) => void onApply(event, vacancy.id)}>
                      <div className="space-y-1.5">
                        <Label htmlFor={`cover_${vacancy.id}`}>Сопроводительное письмо (опционально)</Label>
                        <Textarea
                          id={`cover_${vacancy.id}`}
                          rows={3}
                          value={draft.cover}
                          onChange={(event) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [vacancy.id]: { ...draft, cover: event.target.value },
                            }))
                          }
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor={`note_${vacancy.id}`}>Комментарий</Label>
                        <Input
                          id={`note_${vacancy.id}`}
                          value={draft.note}
                          onChange={(event) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [vacancy.id]: { ...draft, note: event.target.value },
                            }))
                          }
                        />
                      </div>
                      <Button type="submit" disabled={busyVacancyId === vacancy.id}>
                        {busyVacancyId === vacancy.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                        Откликнуться
                      </Button>
                    </form>
                  )}
                </NeonCardContent>
              </NeonCard>
            )
          })}
        </div>
      )}
    </div>
  )
}
