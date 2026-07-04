'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { fetchHealth } from '@/lib/api'
import { stats } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

// ── Local Types ────────────────────────────────────────────────────────────────
type HealthStatus = 'checking' | 'healthy' | 'unreachable'

const indicatorColor = {
  success: 'bg-success',
  warning: 'bg-warning',
  critical: 'bg-critical',
} as const

export function StatCards() {
  const [health, setHealth] = useState<HealthStatus>('checking')

  useEffect(() => {
    // AbortController allows us to cancel in-flight requests when the component
    // unmounts, preventing "state update on unmounted component" React warnings.
    const controller = new AbortController()

    async function checkHealth() {
      try {
        await fetchHealth(controller.signal)
        // If fetchHealth resolves without throwing, the backend is reachable.
        setHealth('healthy')
      } catch (err) {
        // AbortError fires on component unmount — silently ignore it.
        // Any other error means the backend is unreachable.
        if (err instanceof Error && err.name !== 'AbortError') {
          setHealth('unreachable')
        }
      }
    }

    void checkHealth()
    // Re-poll every 30 seconds to keep the status badge current.
    const interval = setInterval(checkHealth, 30_000)

    return () => {
      controller.abort()
      clearInterval(interval)
    }
  }, [])

  const healthBadgeClass =
    health === 'healthy'
      ? 'bg-success/10 text-success'
      : health === 'unreachable'
        ? 'bg-critical/10 text-critical'
        : 'bg-muted text-muted-foreground'

  const healthLabel =
    health === 'checking' ? 'Checking…' : health === 'healthy' ? 'Online' : 'Offline'
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {/* Live backend health card */}
      <Card className="shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md hover:ring-primary/20">
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">Backend API</span>
            <span className="relative flex size-2.5">
              {health === 'healthy' && (
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-60" />
              )}
              <span
                className={cn(
                  'relative inline-flex size-2.5 rounded-full',
                  health === 'healthy' ? 'bg-success' : health === 'unreachable' ? 'bg-critical' : 'bg-muted-foreground',
                )}
              />
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <Badge variant="secondary" className={healthBadgeClass}>
              {healthLabel}
            </Badge>
            <span className="text-sm text-muted-foreground">port 8000</span>
          </div>
        </CardContent>
      </Card>
      {stats.map((stat) => (
        <Card
          key={stat.label}
          className="shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md hover:ring-primary/20"
        >
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-muted-foreground">{stat.label}</span>
              {stat.indicator ? (
                <span className="relative flex size-2.5">
                  <span
                    className={cn(
                      'absolute inline-flex size-full animate-ping rounded-full opacity-60',
                      indicatorColor[stat.indicator],
                    )}
                  />
                  <span className={cn('relative inline-flex size-2.5 rounded-full', indicatorColor[stat.indicator])} />
                </span>
              ) : null}
              {stat.badge ? (
                <Badge variant="secondary" className="bg-success/10 text-success">
                  {stat.badge}
                </Badge>
              ) : null}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="whitespace-nowrap font-mono text-3xl font-semibold tracking-tight">{stat.value}</span>
              {stat.caption ? <span className="text-sm text-balance text-muted-foreground">{stat.caption}</span> : null}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
