'use client'

import { FormEvent, useState } from 'react'
import { KeyRound, Loader2 } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'

export default function CandidateSettingsPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (newPassword !== confirmPassword) {
      setError('Новый пароль и подтверждение не совпадают')
      return
    }

    setSaving(true)
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setSuccess('Пароль успешно изменен. В остальных сессиях потребуется повторный вход.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить пароль')
    } finally {
      setSaving(false)
    }
  }

  return (
    <NeonCard>
      <NeonCardHeader>
        <NeonCardTitle>Настройки безопасности</NeonCardTitle>
      </NeonCardHeader>
      <NeonCardContent>
        <form onSubmit={onSubmit} className="max-w-xl space-y-4">
          {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
          {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{success}</div> : null}

          <div className="space-y-1.5">
            <Label htmlFor="current_password">Текущий пароль</Label>
            <Input id="current_password" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="new_password">Новый пароль</Label>
            <Input id="new_password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirm_password">Подтверждение нового пароля</Label>
            <Input id="confirm_password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />
          </div>

          <Button type="submit" disabled={saving}>
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KeyRound className="mr-2 h-4 w-4" />}
            Сменить пароль
          </Button>
        </form>
      </NeonCardContent>
    </NeonCard>
  )
}
