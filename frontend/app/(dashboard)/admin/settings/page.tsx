'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Loader2, Plus } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type InterviewQuestionBankItem, type Vacancy } from '@/lib/api'

export default function AdminSettingsPage() {
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [questionBank, setQuestionBank] = useState<InterviewQuestionBankItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState({
    vacancy_id: '',
    stage: 'intro' as 'intro' | 'theory' | 'ide',
    question_text: '',
    expected_difficulty: 3,
    metadata_json: '{"source":"admin-settings"}',
  })

  const load = async () => {
    const [vacancyList, bankList] = await Promise.all([api.listVacancies(200), api.listInterviewQuestionBank()])
    setVacancies(vacancyList)
    setQuestionBank(bankList)

    if (!form.vacancy_id && vacancyList.length) {
      setForm((prev) => ({ ...prev, vacancy_id: vacancyList[0].id }))
    }
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить справочники')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onCreateQuestion = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)

    try {
      await api.createInterviewQuestionBankItem({
        vacancy_id: form.vacancy_id || undefined,
        stage: form.stage,
        question_text: form.question_text,
        expected_difficulty: form.expected_difficulty,
        metadata_json: JSON.parse(form.metadata_json || '{}'),
      })
      setForm((prev) => ({ ...prev, question_text: '' }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить вопрос')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем справочники…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Справочник вопросов AI-интервью</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onCreateQuestion} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="vacancy_id">Вакансия</Label>
                <select id="vacancy_id" value={form.vacancy_id} onChange={(e) => setForm((p) => ({ ...p, vacancy_id: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  <option value="">Все вакансии</option>
                  {vacancies.map((vacancy) => (
                    <option key={vacancy.id} value={vacancy.id}>{vacancy.title}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="stage">Этап</Label>
                <select id="stage" value={form.stage} onChange={(e) => setForm((p) => ({ ...p, stage: e.target.value as 'intro' | 'theory' | 'ide' }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  <option value="intro">Вводный</option>
                  <option value="theory">Теория</option>
                  <option value="ide">Практика IDE</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="difficulty">Сложность</Label>
                <Input id="difficulty" type="number" min={1} max={5} value={form.expected_difficulty} onChange={(e) => setForm((p) => ({ ...p, expected_difficulty: Number(e.target.value || 3) }))} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="question_text">Вопрос</Label>
              <Textarea id="question_text" rows={3} value={form.question_text} onChange={(e) => setForm((p) => ({ ...p, question_text: e.target.value }))} required />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="metadata_json">JSON метаданных</Label>
              <Textarea id="metadata_json" rows={2} value={form.metadata_json} onChange={(e) => setForm((p) => ({ ...p, metadata_json: e.target.value }))} />
            </div>
            <Button type="submit" disabled={saving}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}Добавить вопрос</Button>
          </form>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Текущий банк вопросов</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          {!questionBank.length ? (
            <p className="text-sm text-muted-foreground">Банк вопросов пуст.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {questionBank.slice(0, 100).map((item) => (
                <div key={item.id} className="rounded-md border border-border/50 p-2">
                  <p className="font-medium">[{item.stage}] {item.question_text}</p>
                  <p className="text-xs text-muted-foreground">Сложность: {item.expected_difficulty} · Активен: {item.is_active ? 'да' : 'нет'}</p>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
