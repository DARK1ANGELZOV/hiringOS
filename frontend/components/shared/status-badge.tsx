import { cn } from '@/lib/utils'
import { candidateStatusColors, statusLabel } from '@/lib/status'

interface StatusBadgeProps {
  status: string
  className?: string
  size?: 'sm' | 'md'
}

export function StatusBadge({ status, className, size = 'md' }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium',
        candidateStatusColors[status] ?? 'bg-slate-500/10 text-slate-300 border-slate-400/30',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
        className
      )}
    >
      {statusLabel(status)}
    </span>
  )
}
