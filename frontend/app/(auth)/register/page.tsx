'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowRight, Loader2 } from 'lucide-react'

import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const rolePath: Record<string, string> = {
  candidate: '/candidate',
}

export default function RegisterPage() {
  const router = useRouter()
  const { register } = useAuth()

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setIsLoading(true)

    const result = await register({
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      password: form.password,
    })

    setIsLoading(false)
    if (!result.success) {
      setError(result.error)
      return
    }

    router.replace(rolePath.candidate)
    setTimeout(() => router.refresh(), 0)
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-border/60 bg-card/80 p-6 shadow-2xl backdrop-blur">
        <div className="mb-6 space-y-2 text-center">
          <h1 className="text-2xl font-semibold">Регистрация в HiringOS</h1>
          <p className="text-sm text-muted-foreground">Создайте аккаунт и начните работу в системе подбора</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}

          <div className="space-y-1.5">
            <Label htmlFor="full_name">ФИО</Label>
            <Input
              id="full_name"
              value={form.full_name}
              onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
              required
              disabled={isLoading}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">Эл. почта</Label>
            <Input
              id="email"
              type="email"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              required
              disabled={isLoading}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              minLength={8}
              required
              disabled={isLoading}
            />
          </div>

          <p className="rounded-md border border-border/60 bg-secondary/20 p-2 text-xs text-muted-foreground">
            Через открытую регистрацию создается только роль кандидата. Роли HR/Manager выдаются только через приглашение организации.
          </p>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
            Зарегистрироваться
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-muted-foreground">
          Уже есть аккаунт?{' '}
          <Link href="/login" className="text-primary hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  )
}
