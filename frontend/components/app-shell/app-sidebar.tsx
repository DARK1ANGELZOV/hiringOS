'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  User,
  FileText,
  FolderOpen,
  Calendar,
  Briefcase,
  Users,
  ClipboardList,
  Code,
  Settings,
  Shield,
  BookOpen,
  LogOut,
  ChevronDown,
} from 'lucide-react'

import { useAuth } from '@/contexts/auth-context'
import type { UserRole } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

interface NavItem {
  title: string
  url: string
  icon: React.ElementType
  roles: UserRole[]
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const navigation: NavGroup[] = [
  {
    label: 'Главное',
    items: [
      { title: 'Дашборд кандидата', url: '/candidate', icon: LayoutDashboard, roles: ['candidate'] },
      { title: 'Дашборд HR', url: '/hr', icon: LayoutDashboard, roles: ['hr'] },
      { title: 'Дашборд руководителя', url: '/manager', icon: LayoutDashboard, roles: ['manager'] },
      { title: 'Админ-панель', url: '/admin', icon: LayoutDashboard, roles: ['admin'] },
    ],
  },
  {
    label: 'Кандидат',
    items: [
      { title: 'Профиль', url: '/candidate/profile', icon: User, roles: ['candidate'] },
      { title: 'Резюме', url: '/candidate/resume', icon: FileText, roles: ['candidate'] },
      { title: 'Документы', url: '/candidate/documents', icon: FolderOpen, roles: ['candidate'] },
      { title: 'Собеседования', url: '/candidate/interviews', icon: Calendar, roles: ['candidate'] },
      { title: 'Вакансии', url: '/candidate/vacancies', icon: Briefcase, roles: ['candidate'] },
      { title: 'Настройки', url: '/candidate/settings', icon: Settings, roles: ['candidate'] },
    ],
  },
  {
    label: 'Найм',
    items: [
      { title: 'Кандидаты', url: '/hr/candidates', icon: Users, roles: ['hr', 'admin', 'manager'] },
      { title: 'Интервью', url: '/hr/interviews', icon: Calendar, roles: ['hr', 'admin', 'manager'] },
      { title: 'Тесты и скрининг', url: '/screening', icon: Code, roles: ['hr', 'admin', 'manager', 'candidate'] },
      { title: 'Оценка кандидатов', url: '/manager', icon: ClipboardList, roles: ['manager', 'admin'] },
    ],
  },
  {
    label: 'Система',
    items: [
      { title: 'Пользователи', url: '/admin/users', icon: Shield, roles: ['admin'] },
      { title: 'Справочники', url: '/admin/settings', icon: BookOpen, roles: ['admin'] },
      { title: 'Конфигурация', url: '/admin/config', icon: Settings, roles: ['admin'] },
    ],
  },
]

function roleLabel(role: UserRole): string {
  if (role === 'hr') return 'HR'
  if (role === 'manager') return 'Руководитель'
  if (role === 'admin') return 'Администратор'
  return 'Кандидат'
}

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()

  if (!user) return null

  const filteredNavigation = navigation
    .map((group) => ({ ...group, items: group.items.filter((item) => item.roles.includes(user.role)) }))
    .filter((group) => group.items.length > 0)

  const initials = user.name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const onLogout = async () => {
    await logout()
    router.replace('/login')
  }

  return (
    <Sidebar className="border-r border-border/50">
      <SidebarHeader className="border-b border-border/50 p-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 neon-border">
            <div className="h-5 w-5 rounded bg-gradient-to-br from-cyan-400 to-blue-500" />
            <div className="absolute inset-0 rounded-lg bg-cyan-400/10 blur-sm" />
          </div>
          <div>
            <h1 className="text-lg font-semibold gradient-text">HiringOS</h1>
            <p className="text-xs text-muted-foreground">Платформа подбора</p>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent className="px-2 py-4">
        {filteredNavigation.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {group.label}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const isActive = pathname === item.url || pathname.startsWith(`${item.url}/`)
                  return (
                    <SidebarMenuItem key={item.url}>
                      <SidebarMenuButton
                        asChild
                        isActive={isActive}
                        className={cn('relative transition-all duration-200', isActive && 'bg-primary/10 text-primary neon-border')}
                      >
                        <Link href={item.url}>
                          <item.icon className={cn('h-4 w-4', isActive && 'text-primary')} />
                          <span>{item.title}</span>
                          {isActive && <div className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-full bg-primary" />}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="border-t border-border/50 p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-secondary/50 card-hover">
              <Avatar className="h-9 w-9 border border-border">
                <AvatarFallback className="bg-primary/10 text-primary text-sm">{initials}</AvatarFallback>
              </Avatar>
              <div className="flex-1 truncate">
                <p className="text-sm font-medium truncate">{user.name}</p>
                <p className="text-xs text-muted-foreground">{roleLabel(user.role)}</p>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <div className="px-2 py-1.5">
              <p className="text-sm font-medium">{user.name}</p>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onLogout} className="text-destructive focus:text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Выйти
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
