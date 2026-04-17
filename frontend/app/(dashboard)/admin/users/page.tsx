'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Loader2, Shield, UserCog } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, type OrganizationMembership, type UserRole } from '@/lib/api'

interface AdminUserRow {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [memberships, setMemberships] = useState<OrganizationMembership[]>([])
  const [sessions, setSessions] = useState<Array<{
    id: string
    session_id: string
    role: string | null
    org_id: string | null
    revoked_at: string | null
    revoked_reason: string | null
    expires_at: string
    created_at: string
  }>>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [assignForm, setAssignForm] = useState({
    organization_id: '',
    role: 'manager' as UserRole,
    is_owner: false,
  })

  const loadUsers = async () => {
    const rows = await api.adminListUsers(500, 0)
    setUsers(rows)
    if (!selectedUserId && rows.length) {
      setSelectedUserId(rows[0].id)
    }
  }

  const loadSelectedDetails = async (userId: string) => {
    const [membershipRows, sessionRows] = await Promise.all([
      api.listUserMemberships(userId),
      api.listUserSessions(userId),
    ])
    setMemberships(membershipRows)
    setSessions(sessionRows)
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await loadUsers()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить пользователей')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedUserId) return
    void (async () => {
      setBusy(true)
      try {
        await loadSelectedDetails(selectedUserId)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить IAM-данные')
      } finally {
        setBusy(false)
      }
    })()
  }, [selectedUserId])

  const onBlockToggle = async (user: AdminUserRow) => {
    setBusy(true)
    setError(null)
    setSuccess(null)
    try {
      if (user.is_active) {
        await api.blockUser(user.id, 'manual admin action')
      } else {
        await api.unblockUser(user.id)
      }
      await loadUsers()
      if (selectedUserId) await loadSelectedDetails(selectedUserId)
      setSuccess('Статус пользователя обновлен')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить статус пользователя')
    } finally {
      setBusy(false)
    }
  }

  const onRoleChange = async (userId: string, role: UserRole) => {
    setBusy(true)
    setError(null)
    setSuccess(null)
    try {
      await api.updateUserRole(userId, role)
      await loadUsers()
      setSuccess('Роль пользователя обновлена')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить роль')
    } finally {
      setBusy(false)
    }
  }

  const onAssignMembership = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedUserId) return
    setBusy(true)
    setError(null)
    setSuccess(null)

    try {
      await api.assignUserMembership(selectedUserId, {
        organization_id: assignForm.organization_id,
        role: assignForm.role,
        is_owner: assignForm.is_owner,
      })
      await loadSelectedDetails(selectedUserId)
      setSuccess('Membership назначен')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось назначить membership')
    } finally {
      setBusy(false)
    }
  }

  const onMembershipRoleChange = async (membershipId: string, role: UserRole) => {
    if (!selectedUserId) return
    setBusy(true)
    setError(null)
    try {
      await api.updateUserMembership(selectedUserId, membershipId, { role })
      await loadSelectedDetails(selectedUserId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить роль membership')
    } finally {
      setBusy(false)
    }
  }

  const onMembershipActiveToggle = async (membership: OrganizationMembership) => {
    if (!selectedUserId) return
    setBusy(true)
    setError(null)
    try {
      await api.updateUserMembership(selectedUserId, membership.id, { is_active: !membership.is_active })
      await loadSelectedDetails(selectedUserId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить активность membership')
    } finally {
      setBusy(false)
    }
  }

  const onRevokeMembership = async (membershipId: string) => {
    if (!selectedUserId) return
    setBusy(true)
    setError(null)
    try {
      await api.revokeUserMembership(selectedUserId, membershipId)
      await loadSelectedDetails(selectedUserId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отозвать membership')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем IAM-панель…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
      {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{success}</div> : null}

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Пользователи и роли</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          {!users.length ? (
            <p className="text-sm text-muted-foreground">Пользователи не найдены.</p>
          ) : (
            <div className="overflow-auto rounded-lg border border-border/60">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="bg-secondary/40">
                  <tr>
                    <th className="p-2 text-left">Пользователь</th>
                    <th className="p-2 text-left">Роль</th>
                    <th className="p-2 text-left">Статус</th>
                    <th className="p-2 text-left">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className={`border-t border-border/40 ${selectedUserId === user.id ? 'bg-primary/10' : ''}`}>
                      <td className="p-2">
                        <button type="button" className="text-left" onClick={() => setSelectedUserId(user.id)}>
                          <p className="font-medium">{user.full_name}</p>
                          <p className="text-xs text-muted-foreground">{user.email}</p>
                        </button>
                      </td>
                      <td className="p-2">
                        <select
                          value={user.role}
                          onChange={(e) => void onRoleChange(user.id, e.target.value as UserRole)}
                          className="h-8 rounded-md border border-input bg-background px-2"
                          disabled={busy}
                        >
                          <option value="candidate">candidate</option>
                          <option value="hr">hr</option>
                          <option value="manager">manager</option>
                          <option value="admin">admin</option>
                        </select>
                      </td>
                      <td className="p-2">{user.is_active ? 'active' : 'blocked'}</td>
                      <td className="p-2">
                        <Button size="sm" variant={user.is_active ? 'destructive' : 'outline'} onClick={() => void onBlockToggle(user)} disabled={busy}>
                          <UserCog className="mr-2 h-4 w-4" />
                          {user.is_active ? 'Заблокировать' : 'Разблокировать'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </NeonCardContent>
      </NeonCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Memberships пользователя</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-3">
            <form onSubmit={onAssignMembership} className="space-y-2 rounded-md border border-border/50 p-3">
              <div className="space-y-1.5">
                <Label htmlFor="org_id">Organization ID</Label>
                <Input id="org_id" value={assignForm.organization_id} onChange={(e) => setAssignForm((p) => ({ ...p, organization_id: e.target.value }))} required />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="assign_role">Role</Label>
                  <select id="assign_role" value={assignForm.role} onChange={(e) => setAssignForm((p) => ({ ...p, role: e.target.value as UserRole }))} className="h-9 w-full rounded-md border border-input bg-background px-2">
                    <option value="candidate">candidate</option>
                    <option value="hr">hr</option>
                    <option value="manager">manager</option>
                    <option value="admin">admin</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label className="mb-2 block">Owner</Label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={assignForm.is_owner} onChange={(e) => setAssignForm((p) => ({ ...p, is_owner: e.target.checked }))} />
                    is_owner
                  </label>
                </div>
              </div>
              <Button type="submit" size="sm" disabled={busy || !selectedUserId}>Назначить membership</Button>
            </form>

            {!memberships.length ? (
              <p className="text-sm text-muted-foreground">Memberships отсутствуют.</p>
            ) : (
              <div className="space-y-2">
                {memberships.map((membership) => (
                  <div key={membership.id} className="rounded-md border border-border/50 p-2 text-sm">
                    <p className="font-medium">org: {membership.organization_id}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <select
                        value={membership.role}
                        onChange={(e) => void onMembershipRoleChange(membership.id, e.target.value as UserRole)}
                        className="h-8 rounded-md border border-input bg-background px-2"
                        disabled={busy}
                      >
                        <option value="candidate">candidate</option>
                        <option value="hr">hr</option>
                        <option value="manager">manager</option>
                        <option value="admin">admin</option>
                      </select>
                      <Button size="sm" variant="outline" onClick={() => void onMembershipActiveToggle(membership)} disabled={busy}>
                        {membership.is_active ? 'Деактивировать' : 'Активировать'}
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onRevokeMembership(membership.id)} disabled={busy}>
                        Отозвать
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </NeonCardContent>
        </NeonCard>

        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Refresh-сессии пользователя</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            {!sessions.length ? (
              <p className="text-sm text-muted-foreground">Сессии отсутствуют.</p>
            ) : (
              <div className="space-y-2 text-xs">
                {sessions.map((session) => (
                  <div key={session.id} className="rounded-md border border-border/50 p-2">
                    <p className="font-medium">session_id: {session.session_id}</p>
                    <p>role: {session.role || '—'} · org: {session.org_id || '—'}</p>
                    <p>created: {new Date(session.created_at).toLocaleString('ru-RU')}</p>
                    <p>expires: {new Date(session.expires_at).toLocaleString('ru-RU')}</p>
                    <p>revoked: {session.revoked_at ? `${new Date(session.revoked_at).toLocaleString('ru-RU')} (${session.revoked_reason || 'reason: n/a'})` : 'no'}</p>
                  </div>
                ))}
              </div>
            )}
          </NeonCardContent>
        </NeonCard>
      </div>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>RBAC модель</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-2 text-sm">
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Кандидат: только собственные данные.</p>
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />HR: данные в рамках организации.</p>
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Руководитель: только явно назначенные кандидаты.</p>
          <p className="flex items-center gap-2"><Shield className="h-4 w-4 text-primary" />Админ: IAM, аудит, системные операции.</p>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
