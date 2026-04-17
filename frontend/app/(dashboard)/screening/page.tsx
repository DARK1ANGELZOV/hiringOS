'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Loader2, Plus, Sparkles, Play, CheckCircle2 } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type KnowledgeTest, type KnowledgeTestAttempt, type KnowledgeTestDetail, type KnowledgeTestQuestion } from '@/lib/api'
import { testSubtypeLabels } from '@/lib/status'

export default function ScreeningPage() {
  const [tests, setTests] = useState<KnowledgeTest[]>([])
  const [selectedTestId, setSelectedTestId] = useState('')
  const [selectedTest, setSelectedTest] = useState<KnowledgeTestDetail | null>(null)
  const [attempt, setAttempt] = useState<KnowledgeTestAttempt | null>(null)
  const [answerDraft, setAnswerDraft] = useState<Record<string, string>>({})
  const [attemptsHistory, setAttemptsHistory] = useState<KnowledgeTestAttempt[]>([])

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [generateForm, setGenerateForm] = useState({
    title: 'AI тест: backend инженер',
    topic: 'backend',
    subtype: 'theory',
    difficulty: 3,
    question_count: 6,
    company_scope: '',
  })

  const [customForm, setCustomForm] = useState({
    title: 'Кастомный тест компании',
    topic: 'product',
    subtype: 'product',
    difficulty: 3,
    question_text: 'Опишите как бы вы измеряли успех новой функции в продукте.',
    company_scope: '',
  })

  const loadTests = async () => {
    const items = await api.listTests()
    setTests(items)
    if (!selectedTestId && items.length) {
      setSelectedTestId(items[0].id)
    }
  }

  const loadDetails = async (testId: string) => {
    const [detail, attempts] = await Promise.all([api.getTest(testId), api.listTestAttempts({ test_id: testId })])
    setSelectedTest(detail)
    setAttemptsHistory(attempts)
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await loadTests()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить тесты')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedTestId) {
      setSelectedTest(null)
      return
    }

    void (async () => {
      try {
        await loadDetails(selectedTestId)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить детали теста')
      }
    })()
  }, [selectedTestId])

  const onGenerateAiTest = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const created = await api.generateAiTest({
        title: generateForm.title,
        topic: generateForm.topic,
        subtype: generateForm.subtype,
        difficulty: generateForm.difficulty,
        question_count: generateForm.question_count,
        company_scope: generateForm.company_scope || undefined,
        context: { source: 'screening-ui' },
      })
      await loadTests()
      setSelectedTestId(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сгенерировать AI-тест')
    } finally {
      setBusy(false)
    }
  }

  const onCreateCustom = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const created = await api.createCustomTest({
        title: customForm.title,
        topic: customForm.topic,
        subtype: customForm.subtype,
        difficulty: customForm.difficulty,
        company_scope: customForm.company_scope || undefined,
        questions: [
          {
            question_text: customForm.question_text,
            question_type: 'text',
            correct_answer_json: {},
            points: 5,
            metadata_json: { author: 'manager' },
          },
        ],
      })
      await loadTests()
      setSelectedTestId(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать кастомный тест')
    } finally {
      setBusy(false)
    }
  }

  const onStartAttempt = async () => {
    if (!selectedTestId) return
    setBusy(true)
    setError(null)
    try {
      const started = await api.startTestAttempt(selectedTestId)
      setAttempt(started)
      setAnswerDraft({})
      await loadDetails(selectedTestId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить попытку')
    } finally {
      setBusy(false)
    }
  }

  const onSubmitAnswer = async (question: KnowledgeTestQuestion) => {
    if (!attempt) return
    const value = answerDraft[question.id]
    if (!value?.trim()) return

    setBusy(true)
    setError(null)
    try {
      await api.submitTestAnswer(attempt.id, {
        question_id: question.id,
        answer_json: { value },
      })
      await loadDetails(selectedTestId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отправить ответ')
    } finally {
      setBusy(false)
    }
  }

  const onFinishAttempt = async () => {
    if (!attempt) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.finishTestAttempt(attempt.id)
      setAttempt(result.attempt)
      await loadDetails(selectedTestId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось завершить попытку')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем модуль тестов…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Тесты и скрининг</NeonCardTitle></NeonCardHeader>
        <NeonCardContent className="grid gap-3 md:grid-cols-[1fr,220px]">
          <div className="space-y-1.5">
            <Label htmlFor="test_selector">Доступные тесты</Label>
            <select id="test_selector" value={selectedTestId} onChange={(e) => setSelectedTestId(e.target.value)} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
              {!tests.length ? <option value="">Нет тестов</option> : null}
              {tests.map((test) => (
                <option key={test.id} value={test.id}>{test.title} · {testSubtypeLabels[test.subtype] || test.subtype}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button className="w-full" onClick={() => void onStartAttempt()} disabled={!selectedTestId || busy}>
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Начать попытку
            </Button>
          </div>
        </NeonCardContent>
      </NeonCard>

      {selectedTest ? (
        <NeonCard>
          <NeonCardHeader><NeonCardTitle>{selectedTest.title}</NeonCardTitle></NeonCardHeader>
          <NeonCardContent className="space-y-3 text-sm">
            <p>Тема: {selectedTest.topic}</p>
            <p>Подтип: {testSubtypeLabels[selectedTest.subtype] || selectedTest.subtype}</p>
            <p>Сложность: {selectedTest.difficulty}</p>
            <p>Источник: {selectedTest.is_ai_generated ? 'Сгенерирован AI' : 'Кастомный'}</p>
            <p>Количество вопросов: {selectedTest.questions.length}</p>

            {selectedTest.questions.map((question) => (
              <div key={question.id} className="rounded-md border border-border/50 p-3">
                <p className="font-medium">{question.order_index + 1}. {question.question_text}</p>
                <div className="mt-2 flex gap-2">
                  <Input value={answerDraft[question.id] || ''} onChange={(e) => setAnswerDraft((prev) => ({ ...prev, [question.id]: e.target.value }))} placeholder="Введите ответ" />
                  <Button variant="outline" onClick={() => void onSubmitAnswer(question)} disabled={busy || !attempt}>Ответить</Button>
                </div>
              </div>
            ))}

            {attempt ? (
              <Button onClick={() => void onFinishAttempt()} disabled={busy}>
                {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                Завершить попытку
              </Button>
            ) : null}
          </NeonCardContent>
        </NeonCard>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Генерация AI-теста</NeonCardTitle></NeonCardHeader>
          <NeonCardContent>
            <form onSubmit={onGenerateAiTest} className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1.5"><Label htmlFor="gen_title">Название</Label><Input id="gen_title" value={generateForm.title} onChange={(e) => setGenerateForm((p) => ({ ...p, title: e.target.value }))} /></div>
                <div className="space-y-1.5"><Label htmlFor="gen_topic">Тема</Label><Input id="gen_topic" value={generateForm.topic} onChange={(e) => setGenerateForm((p) => ({ ...p, topic: e.target.value }))} /></div>
                <div className="space-y-1.5"><Label htmlFor="gen_subtype">Подтип</Label>
                  <select id="gen_subtype" value={generateForm.subtype} onChange={(e) => setGenerateForm((p) => ({ ...p, subtype: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="algorithms">Алгоритмы</option>
                    <option value="theory">Теория</option>
                    <option value="product">Продуктовая разработка</option>
                  </select>
                </div>
                <div className="space-y-1.5"><Label htmlFor="gen_diff">Сложность (1-5)</Label><Input id="gen_diff" type="number" min={1} max={5} value={generateForm.difficulty} onChange={(e) => setGenerateForm((p) => ({ ...p, difficulty: Number(e.target.value || 3) }))} /></div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1.5"><Label htmlFor="gen_count">Вопросов</Label><Input id="gen_count" type="number" min={3} max={20} value={generateForm.question_count} onChange={(e) => setGenerateForm((p) => ({ ...p, question_count: Number(e.target.value || 6) }))} /></div>
                <div className="space-y-1.5"><Label htmlFor="gen_scope">Область компании</Label><Input id="gen_scope" value={generateForm.company_scope} onChange={(e) => setGenerateForm((p) => ({ ...p, company_scope: e.target.value }))} /></div>
              </div>
              <Button type="submit" disabled={busy}><Sparkles className="mr-2 h-4 w-4" />Сгенерировать</Button>
            </form>
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader><NeonCardTitle>Кастомный тест компании</NeonCardTitle></NeonCardHeader>
          <NeonCardContent>
            <form onSubmit={onCreateCustom} className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1.5"><Label htmlFor="custom_title">Название</Label><Input id="custom_title" value={customForm.title} onChange={(e) => setCustomForm((p) => ({ ...p, title: e.target.value }))} /></div>
                <div className="space-y-1.5"><Label htmlFor="custom_topic">Тема</Label><Input id="custom_topic" value={customForm.topic} onChange={(e) => setCustomForm((p) => ({ ...p, topic: e.target.value }))} /></div>
                <div className="space-y-1.5"><Label htmlFor="custom_subtype">Подтип</Label>
                  <select id="custom_subtype" value={customForm.subtype} onChange={(e) => setCustomForm((p) => ({ ...p, subtype: e.target.value }))} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="algorithms">Алгоритмы</option>
                    <option value="theory">Теория</option>
                    <option value="product">Продуктовая разработка</option>
                  </select>
                </div>
                <div className="space-y-1.5"><Label htmlFor="custom_diff">Сложность</Label><Input id="custom_diff" type="number" min={1} max={5} value={customForm.difficulty} onChange={(e) => setCustomForm((p) => ({ ...p, difficulty: Number(e.target.value || 3) }))} /></div>
              </div>
              <div className="space-y-1.5"><Label htmlFor="custom_question">Вопрос</Label><Textarea id="custom_question" rows={4} value={customForm.question_text} onChange={(e) => setCustomForm((p) => ({ ...p, question_text: e.target.value }))} /></div>
              <div className="space-y-1.5"><Label htmlFor="custom_scope">Область компании</Label><Input id="custom_scope" value={customForm.company_scope} onChange={(e) => setCustomForm((p) => ({ ...p, company_scope: e.target.value }))} /></div>
              <Button type="submit" variant="secondary" disabled={busy}><Plus className="mr-2 h-4 w-4" />Создать кастомный тест</Button>
            </form>
          </NeonCardContent>
        </NeonCard>
      </div>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>История попыток</NeonCardTitle></NeonCardHeader>
        <NeonCardContent>
          {!attemptsHistory.length ? (
            <p className="text-sm text-muted-foreground">Попыток пока нет.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {attemptsHistory.map((item) => (
                <div key={item.id} className="rounded-md border border-border/50 p-2">
                  <p>Попытка: {item.id.slice(0, 8)} · Статус: {item.status}</p>
                  <p className="text-xs text-muted-foreground">Балл: {item.score ?? '—'} / {item.max_score ?? '—'} · {new Date(item.started_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
