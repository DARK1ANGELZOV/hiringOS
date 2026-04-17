'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { useAuth } from '@/contexts/auth-context'

const roleHome: Record<string, string> = {
  candidate: '/candidate',
  hr: '/hr',
  manager: '/manager',
  admin: '/admin',
}

export default function HomePage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    if (isLoading) return

    if (!isAuthenticated) {
      router.replace('/login')
      return
    }

    router.replace(roleHome[user?.role || 'candidate'] || '/candidate')
  }, [isAuthenticated, isLoading, user, router])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Загружаем рабочее пространство…</p>
      </div>
    </div>
  )
}
