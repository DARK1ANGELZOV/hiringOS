'use client'

import Link from 'next/link'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Loader2, Plus, Search } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, type Candidate } from '@/lib/api'
import { statusLabel } from '@/lib/status'

export default function HrCandidatesPage() {
  const [items, setItems] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const [createForm, setCreateForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    location: '',
    headline: '',
    summary: '',
    status: 'new',
  })

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      if (searchText.trim()) {
        const result = await api.searchCandidates(searchText.trim(), 50)
        setItems(result.items.map((entry) => entry.candidate))
      } else {
        const response = await api.listCandidates({ status: statusFilter || undefined, limit: 200 })
        setItems(response.items)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить кандидатов')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter])

  const onCreate = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    try {
      await api.createCandidate({
        full_name: createForm.full_name,
        email: createForm.email || null,
        phone: createForm.phone || null,
        location: createForm.location || null,
        headline: createForm.headline || null,
        summary: createForm.summary || null,
        status: createForm.status,
        skills: [],
        experience: [],
        education: [],
        projects: [],
        languages: [],
      })
      setCreateForm({ full_name: '', email: '', phone: '', location: '', headline: '', summary: '', status: 'new' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать кандидата')
    }
  }

  const statusOptions = useMemo(() => ['new', 'screening', 'hr_interview', 'tech_interview', 'manager_review', 'offer', 'hired', 'rejected'], [])

  return (
    <div className="space-y-6">
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>База кандидатов</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr,220px,auto]">
            <Input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Семантический поиск по навыкам и опыту"
            />
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Все статусы</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {statusLabel(status)}
                </option>
              ))}
            </select>
            <Button onClick={() => void load()}>
              <Search className="mr-2 h-4 w-4" />
              Найти
            </Button>
          </div>

          {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Загружаем кандидатов…
            </div>
          ) : !items.length ? (
            <p className="text-sm text-muted-foreground">Кандидаты пока отсутствуют.</p>
          ) : (
            <div className="overflow-auto rounded-lg border border-border/60">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="bg-secondary/40">
                  <tr>
                    <th className="p-2 text-left">ФИО</th>
                    <th className="p-2 text-left">Должность</th>
                    <th className="p-2 text-left">Контакты</th>
                    <th className="p-2 text-left">Статус</th>
                    <th className="p-2 text-left">Обновлен</th>
                    <th className="p-2 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-border/40">
                      <td className="p-2 font-medium">{item.full_name}</td>
                      <td className="p-2">{item.headline || '—'}</td>
                      <td className="p-2">{item.email || item.phone || '—'}</td>
                      <td className="p-2">{statusLabel(item.status)}</td>
                      <td className="p-2">{new Date(item.updated_at).toLocaleString()}</td>
                      <td className="p-2 text-right">
                        <Button size="sm" variant="outline" asChild>
                          <Link href={`/hr/candidate/${item.id}`}>Открыть</Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Добавить кандидата вручную</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onCreate} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5"><Label htmlFor="new_full_name">ФИО</Label><Input id="new_full_name" value={createForm.full_name} onChange={(e) => setCreateForm((p) => ({ ...p, full_name: e.target.value }))} required /></div>
              <div className="space-y-1.5"><Label htmlFor="new_headline">Желаемая должность</Label><Input id="new_headline" value={createForm.headline} onChange={(e) => setCreateForm((p) => ({ ...p, headline: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="new_email">Эл. почта</Label><Input id="new_email" type="email" value={createForm.email} onChange={(e) => setCreateForm((p) => ({ ...p, email: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="new_phone">Телефон</Label><Input id="new_phone" value={createForm.phone} onChange={(e) => setCreateForm((p) => ({ ...p, phone: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="new_location">Город</Label><Input id="new_location" value={createForm.location} onChange={(e) => setCreateForm((p) => ({ ...p, location: e.target.value }))} /></div>
              <div className="space-y-1.5">
                <Label htmlFor="new_status">Статус</Label>
                <select id="new_status" value={createForm.status} onChange={(e) => setCreateForm((p) => ({ ...p, status: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>{statusLabel(status)}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new_summary">Комментарий</Label>
              <Input id="new_summary" value={createForm.summary} onChange={(e) => setCreateForm((p) => ({ ...p, summary: e.target.value }))} />
            </div>
            <Button type="submit"><Plus className="mr-2 h-4 w-4" />Создать карточку</Button>
          </form>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
