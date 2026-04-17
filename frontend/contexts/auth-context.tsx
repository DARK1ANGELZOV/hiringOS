'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { api, type UserMe, type UserRole } from '@/lib/api'

export type AuthUser = {
  id: string
  email: string
  name: string
  role: UserRole
  createdAt: Date
}

type LoginResult = { success: true } | { success: false; error: string }

type RegisterPayload = {
  email: string
  password: string
  full_name: string
}

interface AuthContextType {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<LoginResult>
  register: (payload: RegisterPayload) => Promise<LoginResult>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function mapMeToUser(me: UserMe): AuthUser {
  return {
    id: me.id,
    email: me.email,
    name: me.full_name,
    role: me.role,
    createdAt: new Date(me.created_at),
  }
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return 'Не удалось выполнить операцию авторизации'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const me = await api.me()
    setUser(mapMeToUser(me))
  }, [])

  useEffect(() => {
    void (async () => {
      try {
        await refreshUser()
      } catch {
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    })()
  }, [refreshUser])

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    setIsLoading(true)
    try {
      await api.login(email, password)
      await refreshUser()
      return { success: true }
    } catch (error) {
      return { success: false, error: toErrorMessage(error) }
    } finally {
      setIsLoading(false)
    }
  }, [refreshUser])

  const register = useCallback(async (payload: RegisterPayload): Promise<LoginResult> => {
    setIsLoading(true)
    try {
      await api.register(payload)
      await refreshUser()
      return { success: true }
    } catch (error) {
      return { success: false, error: toErrorMessage(error) }
    } finally {
      setIsLoading(false)
    }
  }, [refreshUser])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
    }
  }, [])

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, register, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function useRequireRole(allowedRoles: UserRole[]) {
  const { user, isAuthenticated } = useAuth()

  const hasAccess = Boolean(isAuthenticated && user && allowedRoles.includes(user.role))

  return {
    hasAccess,
    user,
    isAuthenticated,
  }
}
