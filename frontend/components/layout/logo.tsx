import { Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground',
        className,
      )}
      aria-hidden="true"
    >
      <Activity className="size-5" strokeWidth={2.5} />
    </div>
  )
}
