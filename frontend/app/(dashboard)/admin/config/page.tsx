'use client'

import { useEffect, useState } from 'react'
import { Loader2, Server, Shield, Brain } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'

type HealthResponse = { status: string }

export default function AdminConfigPage() {
  const [backendHealth, setBackendHealth] = useState<'loading' | 'ok' | 'fail'>('loading')
  const [aiHealth, setAiHealth] = useState<'loading' | 'ok' | 'fail'>('loading')
  const [refreshing, setRefreshing] = useState(false)

  const checkHealth = async () => {
    setRefreshing(true)
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    const backendRoot = apiBase.replace(/\/api\/v1\/?$/, '')
    const aiHealthUrl = process.env.NEXT_PUBLIC_AI_HEALTH_URL || 'http://localhost:8001/healthz'
    try {
      const backend = await fetch(`${backendRoot}/healthz`).then((res) => (res.ok ? res.json() : Promise.reject())) as HealthResponse
      setBackendHealth(backend.status === 'ok' ? 'ok' : 'fail')
    } catch {
      setBackendHealth('fail')
    }

    try {
      const ai = await fetch(aiHealthUrl).then((res) => (res.ok ? res.json() : Promise.reject())) as HealthResponse
      setAiHealth(ai.status === 'ok' ? 'ok' : 'fail')
    } catch {
      setAiHealth('fail')
    }

    setRefreshing(false)
  }

  useEffect(() => {
    void checkHealth()
  }, [])

  return (
    <div className="space-y-6">
      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Системная конфигурация и здоровье сервисов</NeonCardTitle></NeonCardHeader>
        <NeonCardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border/50 p-3 text-sm">
              <p className="mb-1 flex items-center gap-2 font-semibold"><Server className="h-4 w-4 text-primary" />Backend API (бэкенд)</p>
              <p className={backendHealth === 'ok' ? 'text-emerald-300' : backendHealth === 'fail' ? 'text-red-300' : 'text-muted-foreground'}>
                {backendHealth === 'ok' ? 'Работает стабильно' : backendHealth === 'fail' ? 'Недоступен' : 'Проверка…'}
              </p>
            </div>
            <div className="rounded-md border border-border/50 p-3 text-sm">
              <p className="mb-1 flex items-center gap-2 font-semibold"><Brain className="h-4 w-4 text-primary" />AI-сервис</p>
              <p className={aiHealth === 'ok' ? 'text-emerald-300' : aiHealth === 'fail' ? 'text-red-300' : 'text-muted-foreground'}>
                {aiHealth === 'ok' ? 'Работает стабильно' : aiHealth === 'fail' ? 'Недоступен' : 'Проверка…'}
              </p>
            </div>
          </div>
          <Button onClick={() => void checkHealth()} disabled={refreshing}>
            {refreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Обновить статус
          </Button>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Политики безопасности</NeonCardTitle></NeonCardHeader>
        <NeonCardContent className="space-y-2 text-sm">
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />JWT access/refresh с backend-валидацией и RBAC.</p>
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Rate limiting на auth endpoints и чувствительные маршруты.</p>
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Валидация файлов и приватный доступ к медиа интервью.</p>
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Аудит действий администраторов и HR в БД.</p>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader><NeonCardTitle>Локальные AI-модели и лимит ресурсов</NeonCardTitle></NeonCardHeader>
        <NeonCardContent className="space-y-2 text-sm text-muted-foreground">
          <p>В проекте используются локальные модели Hugging Face с fallback-механизмами.</p>
          <p>Целевой бюджет по памяти моделей: до 12 ГБ суммарно.</p>
          <p>При недоступности компонента (STT/TTS/LLM) система продолжает собеседование в деградированном режиме.</p>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
