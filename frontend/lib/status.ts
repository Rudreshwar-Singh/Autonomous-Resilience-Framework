import type { ServiceStatus } from '@/lib/mock-data'

export const statusConfig: Record<
  ServiceStatus,
  { label: string; dot: string; text: string; bg: string }
> = {
  healthy: {
    label: 'Healthy',
    dot: 'bg-success',
    text: 'text-success',
    bg: 'bg-success/10',
  },
  degraded: {
    label: 'Degraded',
    dot: 'bg-warning',
    text: 'text-warning',
    bg: 'bg-warning/10',
  },
  critical: {
    label: 'Critical',
    dot: 'bg-critical',
    text: 'text-critical',
    bg: 'bg-critical/10',
  },
}
