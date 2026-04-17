'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Loader2, Plus, ShieldCheck, Activity, Building2 } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type Vacancy } from '@/lib/api'

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<Record<string, number>>({})
  const [auditLogs, setAuditLogs] = useState<Array<Record<string, unknown>>>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [form, setForm] = useState({
    title: '',
    level: '',
    department: '',
    stack_json: '',
    description: '',
  })

  const load = async () => {
    const [statsData, auditData, vacanciesData] = await Promise.all([
      api.adminStats(),
      api.adminAuditLogs(200),
      api.listVacancies(200),
    ])
    setStats(statsData)
    setAuditLogs(auditData)
    setVacancies(vacanciesData)
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить админ-дашборд')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const onCreateVacancy = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createVacancy({
        title: form.title,
        level: form.level,
        department: form.department || undefined,
        stack_json: form.stack_json
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        description: form.description || undefined,
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать вакансию')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем админ-дашборд…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Системные метрики</NeonCardTitle></NeonCardHeader>
          <NeonCardContent className="space-y-2 text-sm">
            <p className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" />Пользователи: {stats.users_total ?? 0}</p>
            <p className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" />Кандидаты: {stats.candidates_total ?? 0}</p>
            <p className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" />Интервью: {stats.interviews_total ?? 0}</p>
            <p className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" />Уведомления unread: {stats.notifications_unread ?? 0}</p>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Вакансии</NeonCardTitle></NeonCardHeader>
          <NeonCardContent className="space-y-2 text-sm">
            <p className="flex items-center gap-2"><Building2 className="h-4 w-4 text-primary" />Всего вакансий: {vacancies.length}</p>
            <p className="text-muted-foreground">Управляйте стеком и уровнями должностей для интервьеров и тестов.</p>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Аудит</NeonCardTitle></NeonCardHeader>
          <NeonCardContent className="space-y-2 text-sm">
            <p className="flex items-center gap-2"><Activity className="h-4 w-4 text-primary" />Записей аудита: {auditLogs.length}</p>
            <p className="text-muted-foreground">Фиксируются авторизация, смена статусов, интервью, загрузка документов и admin-действия.</p>
          </NeonCardContent>
        </NeonCard>
      </div>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Создать вакансию</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onCreateVacancy} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5"><Label htmlFor="vac_title">Название</Label><Input id="vac_title" value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="vac_level">Уровень</Label><Input id="vac_level" value={form.level} onChange={(e) => setForm((p) => ({ ...p, level: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="vac_department">Подразделение</Label><Input id="vac_department" value={form.department} onChange={(e) => setForm((p) => ({ ...p, department: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="vac_stack">Стек (через запятую)</Label><Input id="vac_stack" value={form.stack_json} onChange={(e) => setForm((p) => ({ ...p, stack_json: e.target.value }))} /></div>
            </div>
            <div className="space-y-1.5"><Label htmlFor="vac_description">Описание</Label><Textarea id="vac_description" rows={4} value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} /></div>
            <Button type="submit" disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}Добавить вакансию</Button>
          </form>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Последние записи аудита</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          {!auditLogs.length ? (
            <p className="text-sm text-muted-foreground">Записи аудита отсутствуют.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {auditLogs.slice(0, 30).map((log, index) => (
                <div key={`${String(log.id || index)}`} className="rounded-md border border-border/50 p-2">
                  <p className="font-medium">{String(log.action || 'action')}</p>
                  <p className="text-muted-foreground">{String(log.created_at || log.timestamp || '—')}</p>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
