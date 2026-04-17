'use client'

import { createContext, useContext, useState, useCallback, useMemo, useEffect, type ReactNode } from 'react'

import { api } from '@/lib/api'

export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface UiNotification {
  id: string
  type: NotificationType
  title: string
  message: string
  read: boolean
  createdAt: Date
}

interface NotificationContextType {
  notifications: UiNotification[]
  unreadCount: number
  refresh: () => Promise<void>
  markAsRead: (id: string) => Promise<void>
  markAllAsRead: () => Promise<void>
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

function inferType(message: string): NotificationType {
  const lower = message.toLowerCase()
  if (lower.includes('ошиб') || lower.includes('fail')) return 'error'
  if (lower.includes('вниман') || lower.includes('risk')) return 'warning'
  if (lower.includes('успеш') || lower.includes('ready') || lower.includes('готов')) return 'success'
  return 'info'
}

function mapNotification(item: {
  id: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}): UiNotification {
  return {
    id: item.id,
    title: item.title,
    message: item.message,
    type: inferType(`${item.title} ${item.message}`),
    read: item.is_read,
    createdAt: new Date(item.created_at),
  }
}

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<UiNotification[]>([])

  const refresh = useCallback(async () => {
    try {
      const payload = await api.listNotifications()
      setNotifications(payload.items.map(mapNotification))
    } catch {
      // Notification feed is non-critical for page rendering.
      setNotifications([])
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const markAsRead = useCallback(async (id: string) => {
    await api.markNotificationRead(id)
    setNotifications((prev) => prev.map((item) => (item.id === id ? { ...item, read: true } : item)))
  }, [])

  const markAllAsRead = useCallback(async () => {
    const unread = notifications.filter((item) => !item.read)
    await Promise.all(unread.map((item) => api.markNotificationRead(item.id)))
    setNotifications((prev) => prev.map((item) => ({ ...item, read: true })))
  }, [notifications])

  const value = useMemo<NotificationContextType>(
    () => ({
      notifications,
      unreadCount: notifications.filter((n) => !n.read).length,
      refresh,
      markAsRead,
      markAllAsRead,
    }),
    [notifications, refresh, markAsRead, markAllAsRead],
  )

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}

interface Toast {
  id: string
  type: NotificationType
  title: string
  message?: string
  duration?: number
}

interface ToastContextType {
  toasts: Toast[]
  showToast: (toast: Omit<Toast, 'id'>) => void
  dismissToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}`
    const newToast: Toast = { ...toast, id }

    setToasts((prev) => [...prev, newToast])

    const duration = toast.duration ?? 5000
    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id))
    }, duration)
  }, [])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }, [])

  return <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>{children}</ToastContext.Provider>
}

export function useToast() {
  const context = useContext(ToastContext)
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
