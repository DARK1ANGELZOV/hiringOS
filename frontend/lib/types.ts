// User and Auth Types
export type UserRole = 'candidate' | 'hr' | 'manager' | 'admin'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  avatar?: string
  phone?: string
  createdAt: Date
}

export interface JWTPayload {
  id: string
  email: string
  role: UserRole
  name: string
  exp: number
}

// Candidate Types
export type CandidateStatus = 
  | 'new'
  | 'screening'
  | 'hr_interview'
  | 'tech_interview'
  | 'manager_review'
  | 'offer'
  | 'hired'
  | 'rejected'

export interface Skill {
  id: string
  name: string
  level: 1 | 2 | 3 | 4 | 5 // 1=beginner, 5=expert
  verified: boolean
  category: string
}

export interface Experience {
  id: string
  company: string
  position: string
  startDate: Date
  endDate?: Date
  current: boolean
  description: string
}

export interface Education {
  id: string
  institution: string
  degree: string
  field: string
  startDate: Date
  endDate?: Date
  current: boolean
}

export interface Document {
  id: string
  name: string
  type: 'resume' | 'certificate' | 'portfolio' | 'other'
  url: string
  uploadedAt: Date
}

export interface Candidate {
  id: string
  userId: string
  user: User
  status: CandidateStatus
  position: string
  department: string
  skills: Skill[]
  experience: Experience[]
  education: Education[]
  documents: Document[]
  salary?: {
    expected: number
    currency: string
  }
  location: string
  workFormat: 'office' | 'remote' | 'hybrid'
  availableFrom?: Date
  notes: string[]
  createdAt: Date
  updatedAt: Date
}

// Interview Types
export type InterviewType = 'hr' | 'technical' | 'manager' | 'final'
export type InterviewStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show'

export interface Interview {
  id: string
  candidateId: string
  type: InterviewType
  status: InterviewStatus
  scheduledAt: Date
  duration: number // in minutes
  interviewers: User[]
  meetingLink?: string
  notes?: string
  feedback?: InterviewFeedback
}

export interface InterviewFeedback {
  id: string
visibleOnly?: boolean // Not used in mock
  interviewId: string
  interviewerId: string
  rating: 1 | 2 | 3 | 4 | 5
  strengths: string[]
  weaknesses: string[]
  recommendation: 'strong_hire' | 'hire' | 'no_hire' | 'strong_no_hire'
  comments: string
  createdAt: Date
}

// Evaluation Types
export interface ManagerEvaluation {
  id: string
  candidateId: string
  managerId: string
  technicalSkills: number // 1-5
  communication: number // 1-5
  teamFit: number // 1-5
  motivation: number // 1-5
  overall: number // 1-5
  strengths: string[]
  concerns: string[]
  recommendation: 'approve' | 'reject' | 'additional_interview'
  comments: string
  createdAt: Date
}

// Screening Types
export interface CodingTask {
  id: string
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  timeLimit: number // in minutes
  language: string
  starterCode: string
  testCases: TestCase[]
}

export interface TestCase {
  id: string
  input: string
  expectedOutput: string
  isHidden: boolean
}

export interface ScreeningSession {
  id: string
  candidateId: string
  taskId: string
  startedAt: Date
  completedAt?: Date
  code: string
  testResults: TestResult[]
  trustScore: number // 0-100
  tabSwitches: number
  copyPasteEvents: number
}

export interface TestResult {
  testCaseId: string
  passed: boolean
  actualOutput: string
  executionTime: number // in ms
}

// Notification Types
export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface Notification {
  id: string
  userId: string
  type: NotificationType
  title: string
  message: string
  read: boolean
  actionUrl?: string
  createdAt: Date
}

// KPI Types
export interface HRMetrics {
  totalCandidates: number
  newThisWeek: number
  inProgress: number
  hired: number
  rejected: number
  averageTimeToHire: number // in days
  conversionRate: number // percentage
  interviewsScheduled: number
  pendingRequests: number
}

// Activity Log
export interface ActivityLog {
  id: string
  userId: string
  action: string
  entityType: 'candidate' | 'interview' | 'user' | 'system'
  entityId: string
  details: Record<string, unknown>
  createdAt: Date
}

// Admin Types
export interface SystemSettings {
  id: string
  key: string
  value: string
  description: string
  category: 'general' | 'notifications' | 'security' | 'integrations'
}

// Navigation Types
export interface NavItem {
  title: string
  url: string
  icon: string
  roles: UserRole[]
  badge?: number
  children?: NavItem[]
}

// Command Palette Types
export interface Command {
  id: string
  title: string
  description?: string
  icon?: string
  shortcut?: string
  action: () => void
  category: 'navigation' | 'action' | 'search'
  roles?: UserRole[]
}
