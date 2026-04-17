'use client'

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Download, Loader2, Save, Sparkles, Upload } from 'lucide-react'

import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from '@/components/shared/neon-card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, type Candidate, type DocumentItem, type ProfileOption, type ResumeProfile } from '@/lib/api'
import { loadOwnCandidate } from '@/lib/candidate-utils'

type FillMode = 'manual' | 'ai'

function splitSkills(raw: string): string[] {
  const normalized = raw
    .replaceAll('\n', ',')
    .replaceAll(';', ',')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
  return Array.from(new Set(normalized))
}

export default function CandidateProfilePage() {
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [resume, setResume] = useState<ResumeProfile | null>(null)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [languageOptions, setLanguageOptions] = useState<ProfileOption[]>([])
  const [mode, setMode] = useState<FillMode>('manual')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [uploadingCertificate, setUploadingCertificate] = useState(false)
  const [customLanguageInput, setCustomLanguageInput] = useState('')
  const [resumeText, setResumeText] = useState('')

  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    city: '',
    location: '',
    citizenship: '',
    linkedin_url: '',
    github_url: '',
    portfolio_url: '',
    desired_position: '',
    specialization: '',
    level: '',
    headline: '',
    summary: '',
    salary_expectation: '',
    employment_type: '',
    work_format: '',
    work_schedule: '',
    relocation_ready: false,
    travel_ready: false,
    skills_raw: '',
    competencies_raw: '',
    languages_raw: '',
  })

  const selectedSkillTags = useMemo(() => splitSkills(form.skills_raw), [form.skills_raw])
  const certificateDocuments = useMemo(
    () => documents.filter((item) => item.document_type === 'certificate'),
    [documents],
  )

  const hydrateForm = (item: Candidate | null) => {
    if (!item) return
    setForm({
      full_name: item.full_name,
      email: item.email || '',
      phone: item.phone || '',
      date_of_birth: item.date_of_birth || '',
      city: item.city || '',
      location: item.location || '',
      citizenship: item.citizenship || '',
      linkedin_url: item.linkedin_url || '',
      github_url: item.github_url || '',
      portfolio_url: item.portfolio_url || '',
      desired_position: item.desired_position || '',
      specialization: item.specialization || '',
      level: item.level || '',
      headline: item.headline || '',
      summary: item.summary || '',
      salary_expectation: item.salary_expectation || '',
      employment_type: item.employment_type || '',
      work_format: item.work_format || '',
      work_schedule: item.work_schedule || '',
      relocation_ready: Boolean(item.relocation_ready),
      travel_ready: Boolean(item.travel_ready),
      skills_raw: item.skills_raw || '',
      competencies_raw: item.competencies_raw || '',
      languages_raw: item.languages_raw || '',
    })
  }

  const reloadBundle = useCallback(async () => {
    const [own, options] = await Promise.all([
      loadOwnCandidate(),
      api.listProgrammingLanguageOptions().catch(() => []),
    ])
    setCandidate(own)
    setLanguageOptions(options)

    if (!own) {
      setResume(null)
      setDocuments([])
      return
    }

    const [resumeProfile, docs] = await Promise.all([
      api.getResumeProfile(own.id).catch(() => null),
      api.listDocuments(own.id).catch(() => []),
    ])
    setResume(resumeProfile)
    setDocuments(docs)
    hydrateForm(own)
  }, [])

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await reloadBundle()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить профиль')
      } finally {
        setLoading(false)
      }
    })()
  }, [reloadBundle])

  const appendSkillTag = (value: string) => {
    const clean = value.trim()
    if (!clean) return
    const merged = Array.from(new Set([...selectedSkillTags, clean]))
    setForm((prev) => ({ ...prev, skills_raw: merged.join(', ') }))
  }

  const removeSkillTag = (value: string) => {
    const merged = selectedSkillTags.filter((item) => item.toLowerCase() !== value.toLowerCase())
    setForm((prev) => ({ ...prev, skills_raw: merged.join(', ') }))
  }

  const onCreateLanguageOption = async () => {
    const value = customLanguageInput.trim()
    if (!value) return

    setError(null)
    try {
      const created = await api.createProgrammingLanguageOption(value)
      setLanguageOptions((prev) => {
        if (prev.some((item) => item.value.toLowerCase() === created.value.toLowerCase())) return prev
        return [...prev, created].sort((left, right) => left.value.localeCompare(right.value, 'ru-RU'))
      })
      appendSkillTag(created.value)
      setCustomLanguageInput('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить язык в общий список')
    }
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const payload = {
        full_name: form.full_name,
        email: form.email || null,
        phone: form.phone || null,
        date_of_birth: form.date_of_birth || null,
        city: form.city || null,
        location: form.location || null,
        citizenship: form.citizenship || null,
        linkedin_url: form.linkedin_url || null,
        github_url: form.github_url || null,
        portfolio_url: form.portfolio_url || null,
        desired_position: form.desired_position || null,
        specialization: form.specialization || null,
        level: form.level || null,
        headline: form.headline || null,
        summary: form.summary || null,
        salary_expectation: form.salary_expectation || null,
        employment_type: form.employment_type || null,
        work_format: form.work_format || null,
        work_schedule: form.work_schedule || null,
        relocation_ready: form.relocation_ready,
        travel_ready: form.travel_ready,
        skills_raw: form.skills_raw || null,
        competencies_raw: form.competencies_raw || null,
        languages_raw: form.languages_raw || null,
      }

      if (!candidate) {
        const created = await api.createCandidate({
          ...payload,
          status: 'new',
          skills: [],
          experience: [],
          education: [],
          projects: [],
          languages: [],
        })
        setCandidate(created)
        hydrateForm(created)
      } else {
        const updated = await api.updateCandidate(candidate.id, payload)
        setCandidate(updated)
        hydrateForm(updated)
      }

      setSuccess('Профиль успешно сохранен')
      await reloadBundle()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить профиль')
    } finally {
      setSaving(false)
    }
  }

  const onUploadResumeFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !candidate) return

    setParsing(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await api.uploadResume(candidate.id, file)
      await reloadBundle()
      setMode('manual')
      setSuccess(
        response.fallback_used
          ? 'Резюме сохранено, но AI-парсер недоступен. Можно заполнить профиль вручную.'
          : 'Резюме сохранено и профиль автозаполнен через AI. Проверьте поля перед сохранением.',
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить резюме')
    } finally {
      setParsing(false)
    }
  }

  const onParseResumeText = async () => {
    if (!candidate) {
      setError('Сначала сохраните профиль кандидата, затем вставляйте резюме для AI-разбора.')
      return
    }
    if (!resumeText.trim()) return

    setParsing(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await api.parseResumeText(candidate.id, resumeText)
      await reloadBundle()
      setMode('manual')
      setSuccess(
        response.fallback_used
          ? 'Текст резюме сохранен, но AI-парсер недоступен. Заполните поля вручную.'
          : 'Текст резюме разобран AI и применен к профилю.',
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось разобрать текст резюме')
    } finally {
      setParsing(false)
    }
  }

  const onDownloadSavedResume = async () => {
    if (!resume?.document_id) return
    setError(null)
    try {
      const payload = await api.getDocumentDownloadUrl(resume.document_id)
      window.open(payload.download_url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось скачать сохраненное резюме')
    }
  }

  const onUploadCertificate = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !candidate) return

    setUploadingCertificate(true)
    setError(null)
    setSuccess(null)
    try {
      await api.uploadDocument(candidate.id, 'certificate', file)
      await reloadBundle()
      setSuccess('Сертификат добавлен в профиль')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить сертификат')
    } finally {
      setUploadingCertificate(false)
    }
  }

  const onDownloadCertificate = async (documentId: string) => {
    try {
      const payload = await api.getDocumentDownloadUrl(documentId)
      window.open(payload.download_url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось скачать сертификат')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Загружаем профиль…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Способ заполнения профиля</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Выберите, как заполнить профиль: вручную или автоматически через AI по резюме.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <button
              type="button"
              onClick={() => setMode('manual')}
              className={`rounded-md border p-3 text-left transition ${
                mode === 'manual' ? 'border-primary bg-primary/10' : 'border-border/60'
              }`}
            >
              <p className="font-medium">Заполнить вручную</p>
              <p className="text-xs text-muted-foreground">Классическая форма профиля.</p>
            </button>
            <button
              type="button"
              onClick={() => setMode('ai')}
              className={`rounded-md border p-3 text-left transition ${
                mode === 'ai' ? 'border-primary bg-primary/10' : 'border-border/60'
              }`}
            >
              <p className="font-medium">Вставить/загрузить резюме (AI)</p>
              <p className="text-xs text-muted-foreground">AI извлечет поля и автозаполнит карточку.</p>
            </button>
          </div>
        </NeonCardContent>
      </NeonCard>

      {mode === 'ai' ? (
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              AI-автозаполнение из резюме
            </NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-4">
            {!candidate ? (
              <p className="text-sm text-muted-foreground">
                Сначала сохраните базовый профиль (ФИО), после этого можно запускать AI-парсинг.
              </p>
            ) : null}

            <div className="space-y-1.5">
              <Label htmlFor="resume_file">Загрузить файл резюме (PDF / DOC / DOCX)</Label>
              <input id="resume_file" type="file" accept=".pdf,.doc,.docx" onChange={onUploadResumeFile} disabled={parsing || !candidate} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="resume_text">Или вставить текст резюме</Label>
              <Textarea
                id="resume_text"
                rows={8}
                value={resumeText}
                onChange={(event) => setResumeText(event.target.value)}
                placeholder="Вставьте полный текст резюме..."
              />
              <Button type="button" variant="outline" onClick={() => void onParseResumeText()} disabled={parsing || !candidate || !resumeText.trim()}>
                {parsing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                Разобрать текст через AI
              </Button>
            </div>

            {resume ? (
              <div className="rounded-md border border-border/60 p-3 text-sm">
                <p>
                  Статус парсинга: <span className="font-medium">{resume.parser_status}</span>
                </p>
                {resume.parser_error ? <p className="text-red-300">Ошибка: {resume.parser_error}</p> : null}
                {resume.document_id ? (
                  <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => void onDownloadSavedResume()}>
                    <Download className="mr-2 h-4 w-4" />
                    Скачать сохраненное резюме
                  </Button>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Файл резюме не загружен. Сохранен только вставленный текст.
                  </p>
                )}
              </div>
            ) : null}
          </NeonCardContent>
        </NeonCard>
      ) : null}

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Профиль кандидата</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            {error ? <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div> : null}
            {success ? <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{success}</div> : null}

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="full_name">ФИО</Label>
                <Input id="full_name" value={form.full_name} onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))} required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Эл. почта</Label>
                <Input id="email" type="email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="phone">Телефон</Label>
                <Input id="phone" value={form.phone} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="date_of_birth">Дата рождения</Label>
                <Input id="date_of_birth" type="date" value={form.date_of_birth} onChange={(e) => setForm((p) => ({ ...p, date_of_birth: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="city">Город</Label>
                <Input id="city" value={form.city} onChange={(e) => setForm((p) => ({ ...p, city: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="location">Локация</Label>
                <Input id="location" value={form.location} onChange={(e) => setForm((p) => ({ ...p, location: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="citizenship">Гражданство</Label>
                <Input id="citizenship" value={form.citizenship} onChange={(e) => setForm((p) => ({ ...p, citizenship: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="desired_position">Желаемая должность</Label>
                <Input id="desired_position" value={form.desired_position} onChange={(e) => setForm((p) => ({ ...p, desired_position: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="specialization">Специализация</Label>
                <Input id="specialization" value={form.specialization} onChange={(e) => setForm((p) => ({ ...p, specialization: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="level">Уровень</Label>
                <Input id="level" value={form.level} onChange={(e) => setForm((p) => ({ ...p, level: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="salary_expectation">Зарплатные ожидания</Label>
                <Input id="salary_expectation" value={form.salary_expectation} onChange={(e) => setForm((p) => ({ ...p, salary_expectation: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="employment_type">Тип занятости</Label>
                <Input id="employment_type" value={form.employment_type} onChange={(e) => setForm((p) => ({ ...p, employment_type: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="work_format">Формат работы</Label>
                <Input id="work_format" value={form.work_format} onChange={(e) => setForm((p) => ({ ...p, work_format: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="work_schedule">График</Label>
                <Input id="work_schedule" value={form.work_schedule} onChange={(e) => setForm((p) => ({ ...p, work_schedule: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="linkedin_url">LinkedIn</Label>
                <Input id="linkedin_url" value={form.linkedin_url} onChange={(e) => setForm((p) => ({ ...p, linkedin_url: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="github_url">GitHub</Label>
                <Input id="github_url" value={form.github_url} onChange={(e) => setForm((p) => ({ ...p, github_url: e.target.value }))} />
              </div>
              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="portfolio_url">Портфолио</Label>
                <Input id="portfolio_url" value={form.portfolio_url} onChange={(e) => setForm((p) => ({ ...p, portfolio_url: e.target.value }))} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="headline">Заголовок резюме</Label>
              <Input id="headline" value={form.headline} onChange={(e) => setForm((p) => ({ ...p, headline: e.target.value }))} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="summary">О себе</Label>
              <Textarea id="summary" value={form.summary} onChange={(e) => setForm((p) => ({ ...p, summary: e.target.value }))} rows={4} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-md border border-border/60 p-3">
                <Label className="mb-2 block">Готовность к переезду</Label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.relocation_ready} onChange={(e) => setForm((p) => ({ ...p, relocation_ready: e.target.checked }))} />
                  Да
                </label>
              </div>
              <div className="rounded-md border border-border/60 p-3">
                <Label className="mb-2 block">Готовность к командировкам</Label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.travel_ready} onChange={(e) => setForm((p) => ({ ...p, travel_ready: e.target.checked }))} />
                  Да
                </label>
              </div>
            </div>

            <div className="space-y-2 rounded-md border border-border/60 p-3">
              <Label>Языки программирования (общий список + ручное добавление)</Label>
              <div className="flex flex-wrap gap-2">
                {languageOptions.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => appendSkillTag(item.value)}
                    className="rounded-full border border-border/70 px-3 py-1 text-xs hover:border-primary"
                  >
                    + {item.value}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Input
                  value={customLanguageInput}
                  onChange={(event) => setCustomLanguageInput(event.target.value)}
                  placeholder="Добавить свой язык (например, Elixir)"
                  className="max-w-sm"
                />
                <Button type="button" variant="outline" onClick={() => void onCreateLanguageOption()}>
                  Добавить в общий список
                </Button>
              </div>
              {selectedSkillTags.length ? (
                <div className="flex flex-wrap gap-2">
                  {selectedSkillTags.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => removeSkillTag(item)}
                      className="rounded-full border border-primary/50 bg-primary/10 px-3 py-1 text-xs"
                    >
                      {item} ×
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Пока ничего не выбрано.</p>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="skills_raw">Навыки</Label>
                <Textarea id="skills_raw" rows={8} value={form.skills_raw} onChange={(e) => setForm((p) => ({ ...p, skills_raw: e.target.value }))} placeholder="Python, FastAPI, PostgreSQL" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="competencies_raw">Компетенции</Label>
                <Textarea id="competencies_raw" rows={8} value={form.competencies_raw} onChange={(e) => setForm((p) => ({ ...p, competencies_raw: e.target.value }))} placeholder="Системное мышление, Коммуникация" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="languages_raw">Иностранные языки</Label>
                <Textarea id="languages_raw" rows={8} value={form.languages_raw} onChange={(e) => setForm((p) => ({ ...p, languages_raw: e.target.value }))} placeholder="Русский — C2, Английский — B2" />
              </div>
            </div>

            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Сохранить профиль
            </Button>
          </form>
        </NeonCardContent>
      </NeonCard>

      <NeonCard>
        <NeonCardHeader>
          <NeonCardTitle>Сертификаты</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-3">
          {!candidate ? (
            <p className="text-sm text-muted-foreground">Сначала сохраните профиль кандидата.</p>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="certificate_file">Загрузить сертификат (PDF / JPG / PNG)</Label>
                <input id="certificate_file" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={onUploadCertificate} disabled={uploadingCertificate} />
              </div>
              <Button type="button" variant="outline" asChild>
                <label htmlFor="certificate_file" className="cursor-pointer">
                  {uploadingCertificate ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                  Добавить сертификат
                </label>
              </Button>
            </>
          )}

          {!certificateDocuments.length ? (
            <p className="text-sm text-muted-foreground">Сертификаты пока не загружены.</p>
          ) : (
            <div className="space-y-2">
              {certificateDocuments.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-md border border-border/60 p-2">
                  <div>
                    <p className="text-sm font-medium">{item.original_filename}</p>
                    <p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString('ru-RU')}</p>
                  </div>
                  <Button type="button" size="sm" variant="outline" onClick={() => void onDownloadCertificate(item.id)}>
                    <Download className="mr-2 h-4 w-4" />
                    Скачать
                  </Button>
                </div>
              ))}
            </div>
          )}
        </NeonCardContent>
      </NeonCard>
    </div>
  )
}
