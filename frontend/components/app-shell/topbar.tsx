'use client'

import { useState } from 'react'
import { Bell, Search, Command, MessageSquare, Check, Info, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

import { useNotifications } from '@/contexts/notification-context'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { SidebarTrigger } from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

interface TopbarProps {
  onOpenCommandPalette: () => void
  onToggleAIPanel: () => void
  isAIPanelOpen: boolean
}

function notificationIcon(type: string) {
  if (type === 'success') return <CheckCircle className="h-4 w-4 text-green-400" />
  if (type === 'warning') return <AlertTriangle className="h-4 w-4 text-yellow-400" />
  if (type === 'error') return <XCircle className="h-4 w-4 text-red-400" />
  return <Info className="h-4 w-4 text-blue-400" />
}

function relativeTime(date: Date): string {
  const now = Date.now()
  const diffMs = now - date.getTime()
  const minutes = Math.floor(diffMs / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days} дн. назад`
  if (hours > 0) return `${hours} ч. назад`
  if (minutes > 0) return `${minutes} мин. назад`
  return 'Только что'
}

export function Topbar({ onOpenCommandPalette, onToggleAIPanel, isAIPanelOpen }: TopbarProps) {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications()
  const [openNotifications, setOpenNotifications] = useState(false)

  return (
    <header className="flex h-14 items-center justify-between border-b border-border/50 bg-background/80 px-4 backdrop-blur-sm">
      <div className="flex items-center gap-4">
        <SidebarTrigger className="-ml-1" />

        <button
          onClick={onOpenCommandPalette}
          className="flex h-9 w-64 items-center gap-2 rounded-lg border border-border/50 bg-secondary/30 px-3 text-sm text-muted-foreground transition-colors hover:bg-secondary/50 hover:border-primary/30"
        >
          <Search className="h-4 w-4" />
          <span className="flex-1 text-left">Поиск и команды…</span>
          <kbd className="flex items-center gap-0.5 rounded border border-border/50 bg-background/50 px-1.5 py-0.5 text-xs">
            <Command className="h-3 w-3" />
            <span>K</span>
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleAIPanel}
          className={cn('relative transition-all', isAIPanelOpen && 'bg-primary/10 text-primary')}
        >
          <MessageSquare className="h-5 w-5" />
          {isAIPanelOpen && <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary animate-pulse" />}
        </Button>

        <DropdownMenu open={openNotifications} onOpenChange={setOpenNotifications}>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-96">
            <div className="flex items-center justify-between px-3 py-2">
              <h3 className="font-medium">Уведомления</h3>
              {unreadCount > 0 && (
                <button onClick={() => void markAllAsRead()} className="flex items-center gap-1 text-xs text-primary hover:underline">
                  <Check className="h-3 w-3" />
                  Прочитать все
                </button>
              )}
            </div>
            <DropdownMenuSeparator />
            <div className="max-h-96 overflow-y-auto">
              {!notifications.length ? (
                <div className="px-3 py-10 text-center text-sm text-muted-foreground">Уведомлений пока нет</div>
              ) : (
                notifications.slice(0, 8).map((notification) => (
                  <DropdownMenuItem
                    key={notification.id}
                    className={cn('flex cursor-pointer flex-col items-start gap-1 px-3 py-2', !notification.read && 'bg-primary/5')}
                    onClick={() => void markAsRead(notification.id)}
                  >
                    <div className="flex w-full items-start gap-2">
                      {notificationIcon(notification.type)}
                      <div className="flex-1 space-y-0.5">
                        <p className="text-sm font-medium leading-tight">{notification.title}</p>
                        <p className="text-xs text-muted-foreground line-clamp-3">{notification.message}</p>
                      </div>
                      {!notification.read && <span className="mt-1 h-2 w-2 rounded-full bg-primary" />}
                    </div>
                    <span className="text-[10px] text-muted-foreground">{relativeTime(notification.createdAt)}</span>
                  </DropdownMenuItem>
                ))
              )}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
