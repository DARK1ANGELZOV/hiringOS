'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Calendar, ClipboardList, Code, FileText, FolderOpen, LayoutDashboard, LogOut, Search, Settings, Shield, User, Users } from 'lucide-react'

import { useAuth } from '@/contexts/auth-context'
import { api, type Candidate } from '@/lib/api'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [query, setQuery] = useState('')
  const [searchItems, setSearchItems] = useState<Candidate[]>([])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        onOpenChange(!open)
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onOpenChange])

  useEffect(() => {
    if (!user || query.trim().length < 3 || user.role === 'candidate') {
      setSearchItems([])
      return
    }

    const timer = setTimeout(() => {
      void (async () => {
        try {
          const result = await api.searchCandidates(query.trim(), 5)
          setSearchItems(result.items.map((item) => item.candidate))
        } catch {
          setSearchItems([])
        }
      })()
    }, 300)

    return () => clearTimeout(timer)
  }, [query, user])

  const runCommand = useCallback(
    (command: () => void) => {
      onOpenChange(false)
      command()
    },
    [onOpenChange],
  )

  const navigate = useCallback(
    (path: string) => {
      runCommand(() => router.push(path))
    },
    [runCommand, router],
  )

  const navItems = useMemo(() => {
    if (!user) return []

    const common = [{ label: 'Тесты и скрининг', href: '/screening', icon: Code }]

    if (user.role === 'candidate') {
      return [
        { label: 'Дашборд кандидата', href: '/candidate', icon: LayoutDashboard },
        { label: 'Профиль', href: '/candidate/profile', icon: User },
        { label: 'Резюме', href: '/candidate/resume', icon: FileText },
        { label: 'Документы', href: '/candidate/documents', icon: FolderOpen },
        { label: 'Собеседования', href: '/candidate/interviews', icon: Calendar },
        ...common,
      ]
    }

    if (user.role === 'hr') {
      return [
        { label: 'Дашборд HR', href: '/hr', icon: LayoutDashboard },
        { label: 'Кандидаты', href: '/hr/candidates', icon: Users },
        { label: 'Интервью', href: '/hr/interviews', icon: Calendar },
        ...common,
      ]
    }

    if (user.role === 'manager') {
      return [
        { label: 'Дашборд руководителя', href: '/manager', icon: LayoutDashboard },
        { label: 'Кандидаты на оценку', href: '/manager', icon: ClipboardList },
        { label: 'Интервью', href: '/hr/interviews', icon: Calendar },
        ...common,
      ]
    }

    return [
      { label: 'Админ-панель', href: '/admin', icon: Shield },
      { label: 'Пользователи', href: '/admin/users', icon: Users },
      { label: 'Справочники', href: '/admin/settings', icon: Settings },
      { label: 'Конфигурация', href: '/admin/config', icon: Settings },
      { label: 'Кандидаты', href: '/hr/candidates', icon: Users },
      { label: 'Интервью', href: '/hr/interviews', icon: Calendar },
      ...common,
    ]
  }, [user])

  if (!user) return null

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Поиск разделов и кандидатов…" value={query} onValueChange={setQuery} />
      <CommandList>
        <CommandEmpty>Ничего не найдено</CommandEmpty>

        {searchItems.length > 0 && (
          <CommandGroup heading="Кандидаты по смысловому поиску">
            {searchItems.map((candidate) => (
              <CommandItem key={candidate.id} onSelect={() => navigate(`/hr/candidate/${candidate.id}`)}>
                <Search className="mr-2 h-4 w-4" />
                <div className="flex w-full items-center justify-between gap-3">
                  <span>{candidate.full_name}</span>
                  <span className="text-xs text-muted-foreground">{candidate.headline || candidate.status}</span>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        <CommandGroup heading="Навигация">
          {navItems.map((item) => (
            <CommandItem key={item.href} onSelect={() => navigate(item.href)}>
              <item.icon className="mr-2 h-4 w-4" />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />
        <CommandGroup heading="Действия">
          <CommandItem
            onSelect={() =>
              runCommand(() => {
                void logout().then(() => router.replace('/login'))
              })
            }
          >
            <LogOut className="mr-2 h-4 w-4" />
            Выйти
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}

export function useCommandPalette() {
  const [open, setOpen] = useState(false)
  return {
    open,
    setOpen,
    toggle: () => setOpen((prev) => !prev),
  }
}
