export const candidateStatusLabels: Record<string, string> = {
  new: 'Новый',
  screening: 'На рассмотрении',
  hr_interview: 'HR-интервью',
  tech_interview: 'Техническое интервью',
  manager_review: 'Интервью с руководителем',
  interview_done: 'Интервью завершено',
  decision_pending: 'Ожидает решения',
  reserve: 'Резерв',
  offer: 'Оффер',
  hired: 'Принят',
  rejected: 'Отказ',
}

export const candidateStatusColors: Record<string, string> = {
  new: 'bg-slate-500/10 text-slate-300 border-slate-400/30',
  screening: 'bg-blue-500/10 text-blue-300 border-blue-400/30',
  hr_interview: 'bg-indigo-500/10 text-indigo-300 border-indigo-400/30',
  tech_interview: 'bg-purple-500/10 text-purple-300 border-purple-400/30',
  manager_review: 'bg-cyan-500/10 text-cyan-300 border-cyan-400/30',
  interview_done: 'bg-emerald-500/10 text-emerald-300 border-emerald-400/30',
  decision_pending: 'bg-amber-500/10 text-amber-300 border-amber-400/30',
  reserve: 'bg-violet-500/10 text-violet-300 border-violet-400/30',
  offer: 'bg-teal-500/10 text-teal-300 border-teal-400/30',
  hired: 'bg-green-500/10 text-green-300 border-green-400/30',
  rejected: 'bg-rose-500/10 text-rose-300 border-rose-400/30',
}

export function statusLabel(status: string): string {
  return candidateStatusLabels[status] ?? status
}

export const testSubtypeLabels: Record<string, string> = {
  algorithms: 'Алгоритмы',
  theory: 'Теория',
  product: 'Продуктовая разработка',
}
