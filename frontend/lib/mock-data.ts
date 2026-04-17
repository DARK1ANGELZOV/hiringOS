// Intentionally empty: demo/mock entities are disabled by product policy.
// Backend API is the only source of truth.

export const mockUsers: never[] = []
export const mockCandidates: never[] = []
export const mockInterviews: never[] = []
export const mockCodingTasks: never[] = []
export const mockNotifications: never[] = []
export const mockHRMetrics: Record<string, never> = {}
export const mockActivityLog: never[] = []
export const mockEvaluations: never[] = []

export const statusLabels: Record<string, string> = {}
export const statusColors: Record<string, string> = {}

export function getCandidateById(): null {
  return null
}

export function getInterviewsForCandidate(): never[] {
  return []
}

export function getUserById(): null {
  return null
}

export function getCandidatesByStatus(): never[] {
  return []
}

export function getUpcomingInterviews(): never[] {
  return []
}
