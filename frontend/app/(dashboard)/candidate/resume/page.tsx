'use client'

import { ChangeEvent, FormEvent, useEffect, useState } from 'react'
import { Loader2, Upload, Save } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type Candidate, type ResumeProfile } from '@/lib/api'
import { loadOwnCandidate, stringifyPretty } from '@/lib/candidate-utils'

export default function CandidateResumePage() {
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [resume, setResume] = useState<ResumeProfile | null>(null)
  const [structuredJson, setStructuredJson] = useState('{}')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const reload = async () => {
    const own = await loadOwnCandidate()
    setCandidate(own)
    if (!own) {
      setResume(null)
      setStructuredJson('{}')
      return
    }

    try {
      const profile = await api.getResumeProfile(own.id)
      setResume(profile)
      setStructuredJson(stringifyPretty(profile.structured_data || {}))
    } catch {
      setResume(null)
      setStructuredJson('{}')
    }
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await reload()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить резюме')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const onUploadFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !candidate) return

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await api.uploadResume(candidate.id, file)
      setSuccess(
        response.fallback_used
          ? 'Резюме загружено. AI-парсер недоступен, заполните структуру вручную.'
          : 'Резюме загружено и автоматически распознано AI.',
      )
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить резюме')
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const onSaveStructured = async (event: FormEvent) => {
    event.preventDefault()
    if (!resume) return

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const parsed = JSON.parse(structuredJson || '{}') as Record<string, unknown>
      const updated = await api.updateResumeProfile(resume.id, parsed)
      setResume(updated)
      setStructuredJson(stringifyPretty(updated.structured_data || {}))
      setSuccess('Структурированное резюме сохранено')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить структурированные данные')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем резюме…
      </div>
    )
  }

  if (!candidate) {
    return (
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Сначала создайте профиль кандидата</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="text-sm text-muted-foreground">
          Невозможно загрузить резюме, пока не заполнена карточка кандидата.
        </NeonCardContent>
      </NeonCard>
    )
  }

  return (
    <div className="space-y-6">
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Загрузка резюме</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-4">
          {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
          {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{success}</div> : null}

          <div className="space-y-2">
            <Label htmlFor="resume_file">Файл резюме (PDF / DOC / DOCX)</Label>
            <input id="resume_file" type="file" accept=".pdf,.doc,.docx" onChange={onUploadFile} disabled={uploading} />
          </div>

          <div className="text-sm text-muted-foreground">
            {resume ? (
              <>
                Статус парсинга: <span className="font-medium">{resume.parser_status}</span>
                {resume.parser_error ? <div className="text-red-300">Ошибка: {resume.parser_error}</div> : null}
              </>
            ) : (
              'Резюме еще не загружено.'
            )}
          </div>

          {uploading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              AI заполняет структуру резюме…
            </div>
          ) : (
            <Button variant="outline" asChild>
              <label htmlFor="resume_file" className="cursor-pointer">
                <Upload className="mr-2 h-4 w-4" />
                Выбрать файл
              </label>
            </Button>
          )}
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Структурированные данные резюме</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          <form className="space-y-3" onSubmit={onSaveStructured}>
            <Textarea rows={20} value={structuredJson} onChange={(event) => setStructuredJson(event.target.value)} />
            <Button type="submit" disabled={saving || !resume}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Сохранить структуру
            </Button>
          </form>
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
