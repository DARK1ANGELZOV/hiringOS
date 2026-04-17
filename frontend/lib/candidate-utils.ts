import { api, type Candidate } from '@/lib/api'

export async function loadOwnCandidate(): Promise<Candidate | null> {
  const list = await api.listCandidates({ limit: 50 })
  return list.items[0] ?? null
}

export function stringifyPretty(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

export function parseJsonObject(text: string): Record<string, unknown> {
  if (!text.trim()) return {}
  const parsed = JSON.parse(text)
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    return parsed as Record<string, unknown>
  }
  return { value: parsed }
}

export function toArrayValue(value: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
}

export function toStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item)).filter(Boolean)
}
