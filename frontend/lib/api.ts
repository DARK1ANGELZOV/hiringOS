export type UserRole = 'candidate' | 'hr' | 'manager' | 'admin'

export interface UserMe {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface TokenPair {
  access_token: string
  access_token_expires_at: string
  refresh_token: string
  refresh_token_expires_at: string
  token_type: string
}

export interface Candidate {
  id: string
  organization_id: string | null
  owner_user_id: string | null
  created_by_user_id: string | null
  full_name: string
  email: string | null
  phone: string | null
  date_of_birth: string | null
  city: string | null
  location: string | null
  citizenship: string | null
  linkedin_url: string | null
  github_url: string | null
  portfolio_url: string | null
  desired_position: string | null
  specialization: string | null
  level: string | null
  headline: string | null
  summary: string | null
  salary_expectation: string | null
  employment_type: string | null
  work_format: string | null
  work_schedule: string | null
  relocation_ready: boolean | null
  travel_ready: boolean | null
  status: string
  skills_raw: string | null
  competencies_raw: string | null
  languages_raw: string | null
  skills: Array<Record<string, unknown>>
  experience: Array<Record<string, unknown>>
  education: Array<Record<string, unknown>>
  projects: Array<Record<string, unknown>>
  languages: Array<Record<string, unknown>>
  created_at: string
  updated_at: string
}

export interface CandidateListResponse {
  items: Candidate[]
  total: number
}

export interface DocumentItem {
  id: string
  candidate_id: string
  bucket: string
  object_key: string
  original_filename: string
  content_type: string
  size_bytes: number
  document_type: string
  created_at: string
}

export interface CandidateStatusHistoryItem {
  id: string
  candidate_id: string
  previous_status: string | null
  new_status: string
  changed_by_user_id: string | null
  comment: string | null
  metadata_json: Record<string, unknown>
  created_at: string
}

export interface ResumeProfile {
  id: string
  candidate_id: string
  document_id: string | null
  parser_status: string
  parser_error: string | null
  structured_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface InterviewSession {
  id: string
  candidate_id: string
  vacancy_id: string
  interviewer_id: string | null
  mode: 'text' | 'voice' | 'mixed'
  status: string
  current_stage: 'intro' | 'theory' | 'ide' | null
  started_at: string | null
  finished_at: string | null
  analysis_status: 'generation_pending' | 'ready' | 'failed' | 'partial'
  anti_cheat_score: number
  anti_cheat_level: 'low' | 'medium' | 'high' | 'critical'
  title?: string
  scheduled_at?: string | null
  interview_format?: 'online' | 'offline' | 'phone' | null
  meeting_link?: string | null
  meeting_location?: string | null
  scheduling_comment?: string | null
  requested_by_manager_id?: string | null
  candidate_invite_status?: 'pending' | 'accepted' | 'declined'
  manager_invite_status?: 'pending' | 'accepted' | 'declined'
  confirmed_candidate_at?: string | null
  confirmed_manager_at?: string | null
  created_at: string
  updated_at: string
}

export interface InterviewRequestItem {
  id: string
  candidate_id: string
  vacancy_id: string | null
  manager_user_id: string
  hr_user_id: string | null
  requested_mode: 'text' | 'voice' | 'mixed'
  requested_format: 'online' | 'offline' | 'phone'
  requested_time: string | null
  comment: string | null
  status: 'pending' | 'approved' | 'rejected'
  review_comment: string | null
  reviewed_at: string | null
  created_interview_session_id: string | null
  metadata_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface InterviewQuestion {
  id: string
  session_id: string
  stage: 'intro' | 'theory' | 'ide'
  order_index: number
  question_text: string
  question_type: 'text' | 'follow_up' | 'multiple_choice' | 'code_task'
  expected_difficulty: number
  metadata_json: Record<string, unknown>
  created_at: string
}

export interface InterviewProgress {
  answered: number
  total: number
  stage: 'intro' | 'theory' | 'ide' | null
  progress_percent: number
}

export interface InterviewReport {
  generation_status: 'generation_pending' | 'ready' | 'failed' | 'partial'
  summary_text: string | null
  score_total: number | null
  score_hard_skills: number | null
  score_soft_skills: number | null
  score_communication: number | null
  score_problem_solving: number | null
  score_code_quality: number | null
  score_business_thinking: number | null
  risk_flags_json: Array<Record<string, unknown>>
  recommendations_json: Array<Record<string, unknown>>
  raw_result_json: Record<string, unknown>
}

export interface InterviewLiveParticipant {
  user_id: string
  role: string
  joined_at: string
}

export interface InterviewQuestionBankItem {
  id: string
  created_by_user_id: string
  vacancy_id: string | null
  stage: 'intro' | 'theory' | 'ide'
  question_text: string
  expected_difficulty: number
  metadata_json: Record<string, unknown>
  is_active: boolean
  created_at: string
}

export interface NotificationItem {
  id: string
  title: string
  message: string
  is_read: boolean
  entity_type: string | null
  entity_id: string | null
  created_at: string
}

export interface Vacancy {
  id: string
  title: string
  level: string
  department: string | null
  stack_json: string[]
  description: string | null
  match?: {
    score_percent: number
    matched_skills: string[]
    missing_skills: string[]
  } | null
  created_at: string
  updated_at: string
}

export interface VacancyApplication {
  id: string
  vacancy_id: string
  candidate_id: string
  created_by_user_id: string | null
  status: string
  cover_letter_text: string | null
  note: string | null
  metadata_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ProfileOption {
  id: string
  option_type: string
  value: string
  created_by_user_id: string | null
  created_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  created_by_user_id: string | null
  is_bootstrap: boolean
  created_at: string
  updated_at: string
}

export interface OrganizationMembership {
  id: string
  organization_id: string
  user_id: string
  role: UserRole
  is_owner: boolean
  is_active: boolean
  metadata_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface KnowledgeTestQuestion {
  id: string
  order_index: number
  question_text: string
  question_type: string
  options_json: Array<Record<string, unknown>>
  explanation: string | null
  points: number
  metadata_json: Record<string, unknown>
}

export interface KnowledgeTest {
  id: string
  created_by_user_id: string
  title: string
  topic: string
  subtype: string
  difficulty: number
  is_ai_generated: boolean
  is_custom: boolean
  company_scope: string | null
  config_json: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface KnowledgeTestDetail extends KnowledgeTest {
  questions: KnowledgeTestQuestion[]
}

export interface KnowledgeTestAttempt {
  id: string
  test_id: string
  candidate_id: string
  session_id: string | null
  status: string
  score: number | null
  max_score: number | null
  started_at: string
  finished_at: string | null
  analysis_json: Record<string, unknown>
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1'
const CSRF_COOKIE_NAME = 'hiringos_csrf'

function setTokens(tokens: TokenPair): void {
  void tokens
  // Access/refresh are delivered via HttpOnly cookies set by backend.
}

export function clearTokens(): void {
  // Cookies are invalidated by backend /auth/logout.
}

export function getStoredAccessToken(): string | null {
  // No JS-visible access token in secure cookie mode.
  return null
}

function getCookie(name: string): string | null {
  if (typeof window === 'undefined') return null
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: { auth?: boolean; retryOn401?: boolean } = {},
): Promise<T> {
  const auth = options.auth ?? true
  const retryOn401 = options.retryOn401 ?? true

  const headers = new Headers(init.headers || {})
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const method = (init.method || 'GET').toUpperCase()
  const needsCsrf = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  if (needsCsrf) {
    const csrfToken = getCookie(CSRF_COOKIE_NAME)
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken)
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && auth && retryOn401) {
    const refreshed = await refreshTokens()
    if (refreshed) {
      return request<T>(path, init, { auth, retryOn401: false })
    }
    clearTokens()
  }

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch {
      // no-op
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

async function refreshTokens(): Promise<boolean> {
  try {
    const tokens = await request<TokenPair>(
      '/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({}),
      },
      { auth: false, retryOn401: false },
    )
    setTokens(tokens)
    return true
  } catch {
    return false
  }
}

export const api = {
  async login(email: string, password: string): Promise<TokenPair> {
    const tokens = await request<TokenPair>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      },
      { auth: false },
    )
    setTokens(tokens)
    return tokens
  },

  async register(payload: { email: string; password: string; full_name: string }): Promise<TokenPair> {
    const tokens = await request<TokenPair>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { auth: false },
    )
    setTokens(tokens)
    return tokens
  },

  async acceptInvite(payload: { token: string; email: string; password: string; full_name: string }): Promise<TokenPair> {
    const tokens = await request<TokenPair>(
      '/auth/invite/accept',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      { auth: false },
    )
    setTokens(tokens)
    return tokens
  },

  async me(): Promise<UserMe> {
    return request<UserMe>('/auth/me')
  },

  async logout(): Promise<void> {
    try {
      await request('/auth/logout', { method: 'POST' })
    } finally {
      clearTokens()
    }
  },

  async changePassword(payload: { current_password: string; new_password: string }): Promise<{ message: string }> {
    return request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listCandidates(params?: { status?: string; limit?: number; offset?: number }): Promise<CandidateListResponse> {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request<CandidateListResponse>(`/candidates${suffix}`)
  },

  async searchCandidates(queryText: string, limit = 20): Promise<{ items: Array<{ candidate: Candidate; score: number }> }> {
    return request('/candidates/search', {
      method: 'POST',
      body: JSON.stringify({ query: queryText, limit }),
    })
  },

  async getCandidate(candidateId: string): Promise<Candidate> {
    return request<Candidate>(`/candidates/${candidateId}`)
  },

  async createCandidate(payload: Partial<Candidate>): Promise<Candidate> {
    return request<Candidate>('/candidates', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async updateCandidate(candidateId: string, payload: Partial<Candidate>): Promise<Candidate> {
    return request<Candidate>(`/candidates/${candidateId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async updateCandidateStatus(
    candidateId: string,
    payload: { new_status: string; comment?: string; metadata_json?: Record<string, unknown> },
  ): Promise<Candidate> {
    return request<Candidate>(`/candidates/${candidateId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({
        new_status: payload.new_status,
        comment: payload.comment || null,
        metadata_json: payload.metadata_json || {},
      }),
    })
  },

  async listCandidateStatusHistory(candidateId: string): Promise<CandidateStatusHistoryItem[]> {
    return request<CandidateStatusHistoryItem[]>(`/candidates/${candidateId}/status-history`)
  },

  async listProgrammingLanguageOptions(limit = 500): Promise<ProfileOption[]> {
    return request(`/candidates/profile-options/programming-languages?limit=${limit}`)
  },

  async createProgrammingLanguageOption(value: string): Promise<ProfileOption> {
    return request('/candidates/profile-options/programming-languages', {
      method: 'POST',
      body: JSON.stringify({ value }),
    })
  },

  async listDocuments(candidateId: string): Promise<DocumentItem[]> {
    return request<DocumentItem[]>(`/documents/${candidateId}`)
  },

  async uploadDocument(candidateId: string, documentType: string, file: File): Promise<DocumentItem> {
    const form = new FormData()
    form.append('file', file)
    return request<DocumentItem>(`/documents/${candidateId}?document_type=${documentType}`, {
      method: 'POST',
      body: form,
    })
  },

  async getDocumentDownloadUrl(documentId: string): Promise<{ document_id: string; download_url: string; expires_in_seconds: number }> {
    return request(`/documents/item/${documentId}/download-url`)
  },

  async deleteDocument(documentId: string): Promise<{ message: string }> {
    return request(`/documents/item/${documentId}`, {
      method: 'DELETE',
    })
  },

  async replaceDocument(documentId: string, file: File): Promise<DocumentItem> {
    const form = new FormData()
    form.append('file', file)
    return request(`/documents/item/${documentId}/replace`, {
      method: 'PUT',
      body: form,
    })
  },

  async uploadResume(candidateId: string, file: File): Promise<{ resume_profile_id: string; parser_status: string; structured_data: Record<string, unknown>; fallback_used: boolean }> {
    const form = new FormData()
    form.append('file', file)
    return request(`/resumes/upload/${candidateId}`, {
      method: 'POST',
      body: form,
    })
  },

  async parseResumeText(
    candidateId: string,
    text: string,
  ): Promise<{ resume_profile_id: string; parser_status: string; structured_data: Record<string, unknown>; fallback_used: boolean }> {
    return request(`/resumes/parse-text/${candidateId}`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },

  async getResumeProfile(candidateId: string): Promise<ResumeProfile> {
    return request<ResumeProfile>(`/resumes/candidate/${candidateId}`)
  },

  async updateResumeProfile(resumeId: string, structuredData: Record<string, unknown>): Promise<ResumeProfile> {
    return request<ResumeProfile>(`/resumes/${resumeId}`, {
      method: 'PATCH',
      body: JSON.stringify({ structured_data: structuredData }),
    })
  },

  async listInterviews(candidateId?: string): Promise<InterviewSession[]> {
    const query = candidateId ? `?candidate_id=${candidateId}` : ''
    return request<InterviewSession[]>(`/interviews${query}`)
  },

  async createInterview(payload: {
    candidate_id: string
    vacancy_id: string
    interviewer_id?: string
    mode: 'text' | 'voice' | 'mixed'
    scheduled_at?: string | null
    interview_format?: 'online' | 'offline' | 'phone'
    meeting_link?: string
    meeting_location?: string
    scheduling_comment?: string
    requested_by_manager_id?: string
  }): Promise<InterviewSession> {
    return request<InterviewSession>('/interviews', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async createInterviewRequest(payload: {
    candidate_id: string
    vacancy_id?: string
    requested_mode: 'text' | 'voice' | 'mixed'
    requested_format?: 'online' | 'offline' | 'phone'
    requested_time?: string
    comment?: string
    hr_user_id?: string
    metadata_json?: Record<string, unknown>
  }): Promise<InterviewRequestItem> {
    return request('/interviews/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listInterviewRequests(params?: { status?: string; candidate_id?: string }): Promise<InterviewRequestItem[]> {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.candidate_id) query.set('candidate_id', params.candidate_id)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request(`/interviews/requests${suffix}`)
  },

  async reviewInterviewRequest(
    requestId: string,
    payload: {
      decision: 'approved' | 'rejected'
      review_comment?: string
      vacancy_id?: string
      interviewer_id?: string
      mode?: 'text' | 'voice' | 'mixed'
      scheduled_at?: string
      interview_format?: 'online' | 'offline' | 'phone'
      meeting_link?: string
      meeting_location?: string
      scheduling_comment?: string
    },
  ): Promise<InterviewRequestItem> {
    return request(`/interviews/requests/${requestId}/review`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async getInterview(sessionId: string): Promise<InterviewSession> {
    return request<InterviewSession>(`/interviews/${sessionId}`)
  },

  async startInterview(sessionId: string): Promise<{
    session: InterviewSession
    first_question: InterviewQuestion | null
    progress: InterviewProgress
  }> {
    return request(`/interviews/${sessionId}/start`, {
      method: 'POST',
    })
  },

  async submitInterviewAnswer(
    sessionId: string,
    payload: {
      question_id: string
      answer_text?: string
      answer_code?: string
      answer_json?: Record<string, unknown>
      response_time_ms?: number
      audio_base64?: string
      audio_content_type?: string
      telemetry?: Record<string, unknown>
    },
  ): Promise<{
    accepted: boolean
    current_question_id: string
    next_question: InterviewQuestion | null
    session_status: string
    stage: 'intro' | 'theory' | 'ide' | null
    progress: InterviewProgress
    ai_analysis_status: 'generation_pending' | 'ready' | 'failed' | 'partial'
  }> {
    return request(`/interviews/${sessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async finishInterview(sessionId: string): Promise<{
    status: string
    analysis_status: 'generation_pending' | 'ready' | 'failed' | 'partial'
    analysis_task_id: string | null
  }> {
    return request(`/interviews/${sessionId}/finish`, {
      method: 'POST',
    })
  },

  async updateInterviewSchedule(
    sessionId: string,
    payload: {
      interviewer_id?: string
      scheduled_at: string
      interview_format?: 'online' | 'offline' | 'phone'
      meeting_link?: string
      meeting_location?: string
      scheduling_comment?: string
      candidate_invite_status?: 'pending' | 'accepted' | 'declined'
      manager_invite_status?: 'pending' | 'accepted' | 'declined'
    },
  ): Promise<InterviewSession> {
    return request(`/interviews/${sessionId}/schedule`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async submitInterviewInviteDecision(
    sessionId: string,
    payload: { role: 'candidate' | 'manager'; decision: 'pending' | 'accepted' | 'declined' },
  ): Promise<InterviewSession> {
    return request(`/interviews/${sessionId}/invite/decision`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async getInterviewQuestions(sessionId: string): Promise<{
    items: InterviewQuestion[]
    current_question_id: string | null
  }> {
    return request(`/interviews/${sessionId}/questions`)
  },

  async ingestInterviewEvent(
    sessionId: string,
    eventType: string,
    payloadJson: Record<string, unknown> = {},
  ): Promise<{
    id: string
    session_id: string
    event_type: string
    payload_json: Record<string, unknown>
    created_at: string
  }> {
    return request(`/interviews/${sessionId}/events`, {
      method: 'POST',
      body: JSON.stringify({ event_type: eventType, payload_json: payloadJson }),
    })
  },

  async getInterviewSignals(sessionId: string): Promise<{
    risk_level: 'low' | 'medium' | 'high' | 'critical'
    anti_cheat_score: number
    items: Array<{
      id: string
      signal_type: string
      severity: 'low' | 'medium' | 'high' | 'critical'
      value_json: Record<string, unknown>
      created_at: string
    }>
  }> {
    return request(`/interviews/${sessionId}/signals`)
  },

  async getInterviewReport(sessionId: string): Promise<InterviewReport> {
    return request<InterviewReport>(`/interviews/${sessionId}/report`)
  },

  async uploadInterviewVideoFrame(
    sessionId: string,
    payload: {
      frame_base64: string
      content_type?: string
      captured_at?: string
      telemetry?: Record<string, unknown>
    },
  ): Promise<{ artifact_id: string; queued: boolean; analysis_task_id: string | null }> {
    return request(`/interviews/${sessionId}/video/frame`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async getInterviewLiveState(sessionId: string): Promise<{ session_id: string; participants: InterviewLiveParticipant[] }> {
    return request(`/interviews/${sessionId}/live`)
  },

  async getSpeechDiagnostics(): Promise<{ stt_loaded: boolean; stt_error: string | null; tts_loaded: boolean; tts_error: string | null }> {
    return request('/interviews/speech/diagnostics')
  },

  async createInterviewQuestionBankItem(payload: {
    vacancy_id?: string
    stage: 'intro' | 'theory' | 'ide'
    question_text: string
    expected_difficulty?: number
    metadata_json?: Record<string, unknown>
  }): Promise<InterviewQuestionBankItem> {
    return request('/interviews/question-bank', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listInterviewQuestionBank(params?: { vacancy_id?: string; stage?: 'intro' | 'theory' | 'ide' }): Promise<InterviewQuestionBankItem[]> {
    const query = new URLSearchParams()
    if (params?.vacancy_id) query.set('vacancy_id', params.vacancy_id)
    if (params?.stage) query.set('stage', params.stage)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request(`/interviews/question-bank${suffix}`)
  },

  async createFeedback(payload: {
    session_id: string
    manager_user_id?: string
    overall_rating: number
    strengths: string
    weaknesses: string
    recommendation: string
    comments?: string
  }): Promise<Record<string, unknown>> {
    return request('/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listFeedback(sessionId: string): Promise<Array<Record<string, unknown>>> {
    return request(`/feedback?session_id=${sessionId}`)
  },

  async listNotifications(): Promise<{ items: NotificationItem[]; unread_count: number }> {
    return request('/notifications')
  },

  async markNotificationRead(notificationId: string): Promise<NotificationItem> {
    return request(`/notifications/${notificationId}/read`, {
      method: 'PATCH',
    })
  },

  async adminStats(): Promise<Record<string, number>> {
    return request('/admin/stats')
  },

  async adminAuditLogs(limit = 200): Promise<Array<Record<string, unknown>>> {
    return request(`/admin/audit-logs?limit=${limit}`)
  },

  async adminListUsers(limit = 200, offset = 0): Promise<Array<{
    id: string
    email: string
    full_name: string
    role: UserRole
    is_active: boolean
    created_at: string
    updated_at: string
  }>> {
    return request(`/admin/users?limit=${limit}&offset=${offset}`)
  },

  async blockUser(userId: string, reason?: string): Promise<{
    id: string
    email: string
    full_name: string
    role: UserRole
    is_active: boolean
    created_at: string
    updated_at: string
  }> {
    return request(`/admin/users/${userId}/block`, {
      method: 'PATCH',
      body: JSON.stringify({ reason: reason || null }),
    })
  },

  async unblockUser(userId: string): Promise<{
    id: string
    email: string
    full_name: string
    role: UserRole
    is_active: boolean
    created_at: string
    updated_at: string
  }> {
    return request(`/admin/users/${userId}/unblock`, {
      method: 'PATCH',
    })
  },

  async updateUserRole(userId: string, role: UserRole): Promise<{
    id: string
    email: string
    full_name: string
    role: UserRole
    is_active: boolean
    created_at: string
    updated_at: string
  }> {
    return request(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    })
  },

  async listUserMemberships(userId: string): Promise<OrganizationMembership[]> {
    return request(`/admin/users/${userId}/memberships`)
  },

  async assignUserMembership(
    userId: string,
    payload: { organization_id: string; role: UserRole; is_owner?: boolean },
  ): Promise<OrganizationMembership> {
    return request(`/admin/users/${userId}/memberships`, {
      method: 'POST',
      body: JSON.stringify({
        organization_id: payload.organization_id,
        role: payload.role,
        is_owner: payload.is_owner ?? false,
      }),
    })
  },

  async updateUserMembership(
    userId: string,
    membershipId: string,
    payload: { role?: UserRole; is_active?: boolean },
  ): Promise<OrganizationMembership> {
    return request(`/admin/users/${userId}/memberships/${membershipId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async revokeUserMembership(userId: string, membershipId: string): Promise<OrganizationMembership> {
    return request(`/admin/users/${userId}/memberships/${membershipId}`, {
      method: 'DELETE',
    })
  },

  async listUserSessions(userId: string): Promise<Array<{
    id: string
    user_id: string
    jti: string
    family_id: string
    session_id: string
    org_id: string | null
    role: string | null
    expires_at: string
    revoked_at: string | null
    revoked_reason: string | null
    reuse_detected_at: string | null
    created_at: string
  }>> {
    return request(`/admin/users/${userId}/sessions`)
  },

  async createOrganization(payload: { name: string; slug?: string }): Promise<Organization> {
    return request('/organizations', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async createOrganizationInvite(
    organizationId: string,
    payload: { email: string; role: 'hr' | 'manager'; metadata_json?: Record<string, unknown> },
  ): Promise<{
    id: string
    organization_id: string
    role: 'hr' | 'manager'
    email: string
    expires_at: string
    used_at: string | null
    created_by: string | null
    used_by_user_id: string | null
    created_at: string
    token: string | null
  }> {
    return request(`/organizations/${organizationId}/invites`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listOrganizationMembers(organizationId: string): Promise<OrganizationMembership[]> {
    return request(`/organizations/${organizationId}/members`)
  },

  async listVacancies(limit = 200): Promise<Vacancy[]> {
    return request(`/vacancies?limit=${limit}`)
  },

  async listVacanciesForCandidate(candidateId: string, limit = 200): Promise<Vacancy[]> {
    return request(`/vacancies?candidate_id=${candidateId}&limit=${limit}`)
  },

  async createVacancy(payload: {
    title: string
    level: string
    department?: string
    stack_json?: string[]
    description?: string
  }): Promise<Vacancy> {
    return request('/admin/vacancies', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async applyToVacancy(
    vacancyId: string,
    payload?: { cover_letter_text?: string; note?: string; metadata_json?: Record<string, unknown> },
  ): Promise<VacancyApplication> {
    return request(`/vacancies/${vacancyId}/apply`, {
      method: 'POST',
      body: JSON.stringify({
        cover_letter_text: payload?.cover_letter_text || null,
        note: payload?.note || null,
        metadata_json: payload?.metadata_json || {},
      }),
    })
  },

  async listMyVacancyApplications(): Promise<VacancyApplication[]> {
    return request('/vacancies/my-applications')
  },

  async listVacancyApplications(params?: { vacancy_id?: string; candidate_id?: string; status?: string }): Promise<VacancyApplication[]> {
    const query = new URLSearchParams()
    if (params?.vacancy_id) query.set('vacancy_id', params.vacancy_id)
    if (params?.candidate_id) query.set('candidate_id', params.candidate_id)
    if (params?.status) query.set('status', params.status)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request(`/vacancies/applications${suffix}`)
  },

  async updateVacancyApplicationStatus(
    applicationId: string,
    payload: { status: string; note?: string },
  ): Promise<VacancyApplication> {
    return request(`/vacancies/applications/${applicationId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: payload.status, note: payload.note || null }),
    })
  },

  async listTests(params?: { topic?: string; subtype?: string; my_only?: boolean }): Promise<KnowledgeTest[]> {
    const query = new URLSearchParams()
    if (params?.topic) query.set('topic', params.topic)
    if (params?.subtype) query.set('subtype', params.subtype)
    if (params?.my_only) query.set('my_only', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    const response = await request<{ items: KnowledgeTest[] }>(`/tests${suffix}`)
    return response.items
  },

  async getTest(testId: string): Promise<KnowledgeTestDetail> {
    return request(`/tests/${testId}`)
  },

  async createCustomTest(payload: {
    title: string
    topic: string
    subtype: string
    difficulty: number
    company_scope?: string
    questions: Array<{
      question_text: string
      question_type: string
      options_json?: Array<Record<string, unknown>>
      correct_answer_json?: Record<string, unknown>
      explanation?: string
      points?: number
      metadata_json?: Record<string, unknown>
    }>
  }): Promise<KnowledgeTestDetail> {
    return request('/tests', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async generateAiTest(payload: {
    title: string
    topic: string
    subtype: string
    difficulty: number
    question_count: number
    company_scope?: string
    context?: Record<string, unknown>
  }): Promise<KnowledgeTestDetail> {
    return request('/tests/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async startTestAttempt(testId: string, sessionId?: string): Promise<KnowledgeTestAttempt> {
    return request(`/tests/${testId}/start`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId || null }),
    })
  },

  async submitTestAnswer(
    attemptId: string,
    payload: { question_id: string; answer_json: Record<string, unknown> },
  ): Promise<{ id: string; is_correct: boolean | null; points_earned: number; answer_json: Record<string, unknown> }> {
    return request(`/tests/attempts/${attemptId}/answer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async finishTestAttempt(attemptId: string): Promise<{
    attempt: KnowledgeTestAttempt
    answered_count: number
    total_questions: number
  }> {
    return request(`/tests/attempts/${attemptId}/finish`, {
      method: 'POST',
    })
  },

  async listTestAttempts(params?: { test_id?: string; candidate_id?: string }): Promise<KnowledgeTestAttempt[]> {
    const query = new URLSearchParams()
    if (params?.test_id) query.set('test_id', params.test_id)
    if (params?.candidate_id) query.set('candidate_id', params.candidate_id)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request(`/tests/attempts/list${suffix}`)
  },
}

export async function fileToBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}
