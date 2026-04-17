'use client'

import { useEffect, useRef, useState } from 'react'
import { Bot, Loader2, Send, Sparkles, User, X } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'

type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface AIPanelProps {
  isOpen: boolean
  onClose: () => void
}

const suggestedQuestions = [
  'Как подготовиться к техническому интервью?',
  'Какие навыки сейчас наиболее востребованы?',
  'Помоги оценить кандидата после интервью',
  'Как составить сильное сопроводительное письмо?',
]

const cannedResponses: Record<string, string> = {
  technical:
    'Для техинтервью подготовьте: 1) базовые структуры данных и алгоритмы; 2) примеры архитектурных решений; 3) разбор trade-offs; 4) практику по задачам на время; 5) вопросы к команде.',
  skills:
    'В 2026 году в найме особенно важны: Python/FastAPI, TypeScript/React, DevOps (Docker/K8s), умение работать с AI-инструментами, а также коммуникация и ownership.',
  evaluation:
    'Для оценки кандидата используйте матрицу: hard skills, problem solving, коммуникация, code quality, business thinking и risk signals anti-cheat. Решение принимайте только по совокупности факторов.',
  cover:
    'Сильное письмо: короткое приветствие, мотивация именно к этой компании, 2-3 измеримых достижения, релевантный опыт и четкий CTA на следующий шаг.',
  default:
    'Я AI-помощник HiringOS. Помогу по вопросам найма, интервью, тестов, anti-cheat сигналов и рекомендаций для HR/руководителя.',
}

function pickResponse(query: string): string {
  const lower = query.toLowerCase()
  if (lower.includes('тех') || lower.includes('алгорит')) return cannedResponses.technical
  if (lower.includes('навык') || lower.includes('skill')) return cannedResponses.skills
  if (lower.includes('оцен') || lower.includes('review')) return cannedResponses.evaluation
  if (lower.includes('пись') || lower.includes('cover')) return cannedResponses.cover
  return cannedResponses.default
}

export function AIPanel({ isOpen, onClose }: AIPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Привет! Я AI-помощник HiringOS. Задайте вопрос по найму, интервью или оценке кандидатов.',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [isOpen])

  const send = async () => {
    const text = input.trim()
    if (!text || isLoading) return

    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-u`, role: 'user', content: text, timestamp: new Date() },
    ])
    setInput('')
    setIsLoading(true)

    await new Promise((resolve) => setTimeout(resolve, 600))

    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-a`, role: 'assistant', content: pickResponse(text), timestamp: new Date() },
    ])
    setIsLoading(false)
  }

  const onEnter = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }

  if (!isOpen) return null

  return (
    <aside className="flex h-full w-96 flex-col border-l border-border/50 bg-background/95 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 neon-border">
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-medium">AI-помощник</h2>
            <p className="text-[10px] text-muted-foreground">Локальный режим (без внешних API)</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 px-4">
        <div className="space-y-4 py-4">
          {messages.map((message) => (
            <div key={message.id} className={cn('flex gap-3', message.role === 'user' && 'flex-row-reverse')}>
              <div
                className={cn(
                  'flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full',
                  message.role === 'assistant' ? 'bg-primary/10 text-primary' : 'bg-secondary text-foreground',
                )}
              >
                {message.role === 'assistant' ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
              </div>
              <div
                className={cn(
                  'max-w-[86%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap',
                  message.role === 'assistant' ? 'bg-secondary/50 text-foreground' : 'bg-primary text-primary-foreground',
                )}
              >
                {message.content}
              </div>
            </div>
          ))}

          {isLoading ? (
            <div className="flex gap-3">
              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-secondary/50 px-3 py-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Формирую ответ…
              </div>
            </div>
          ) : null}

          <div ref={endRef} />
        </div>
      </ScrollArea>

      {messages.length <= 2 ? (
        <div className="border-t border-border/50 px-4 py-3">
          <p className="mb-2 text-xs text-muted-foreground">Подсказки:</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestedQuestions.map((question) => (
              <button
                key={question}
                onClick={() => setInput(question)}
                className="rounded-full bg-secondary/50 px-2.5 py-1 text-xs text-foreground transition-colors hover:bg-secondary"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="border-t border-border/50 p-4">
        <div className="flex items-end gap-2 rounded-lg border border-border/50 bg-secondary/30 p-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onEnter}
            placeholder="Задайте вопрос…"
            rows={1}
            className="max-h-24 flex-1 resize-none bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
          />
          <Button size="icon" onClick={() => void send()} disabled={!input.trim() || isLoading} className="h-8 w-8 flex-shrink-0">
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="mt-2 text-center text-[10px] text-muted-foreground">AI может ошибаться — проверяйте критичные решения.</p>
      </div>
    </aside>
  )
}
