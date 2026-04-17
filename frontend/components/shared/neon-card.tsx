import { cn } from '@/lib/utils'

interface NeonCardProps {
  children: React.ReactNode
  className?: string
  glow?: boolean
}

export function NeonCard({ children, className, glow = false }: NeonCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border/50 bg-card/50 p-6 backdrop-blur-sm transition-all',
        glow && 'neon-border',
        'hover:border-primary/30 hover:bg-card/70',
        className
      )}
    >
      {children}
    </div>
  )
}

interface NeonCardHeaderProps {
  children: React.ReactNode
  className?: string
}

export function NeonCardHeader({ children, className }: NeonCardHeaderProps) {
  return (
    <div className={cn('mb-4', className)}>
      {children}
    </div>
  )
}

interface NeonCardTitleProps {
  children: React.ReactNode
  className?: string
}

export function NeonCardTitle({ children, className }: NeonCardTitleProps) {
  return (
    <h3 className={cn('text-lg font-semibold', className)}>
      {children}
    </h3>
  )
}

interface NeonCardDescriptionProps {
  children: React.ReactNode
  className?: string
}

export function NeonCardDescription({ children, className }: NeonCardDescriptionProps) {
  return (
    <p className={cn('text-sm text-muted-foreground', className)}>
      {children}
    </p>
  )
}

interface NeonCardContentProps {
  children: React.ReactNode
  className?: string
}

export function NeonCardContent({ children, className }: NeonCardContentProps) {
  return (
    <div className={cn('', className)}>
      {children}
    </div>
  )
}
