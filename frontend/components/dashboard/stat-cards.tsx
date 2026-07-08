'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { fetchHealth } from '@/lib/api'
import { type GraphPayload } from '@/lib/api'
import { cn } from '@/lib/utils'

type HealthStatus = 'checking' | 'healthy' | 'unreachable'

export function StatCards({ graphProp }: { graphProp?: GraphPayload | null }) {
  const [health, setHealth] = useState<HealthStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()
    async function checkHealth() {
      try {
        await fetchHealth(controller.signal)
        setHealth('healthy')
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setHealth('unreachable')
        }
      }
    }
    void checkHealth()
    const interval = setInterval(checkHealth, 30_000)
    return () => { controller.abort(); clearInterval(interval) }
  }, [])

  const healthBadgeClass =
    health === 'healthy'
      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400'
      : health === 'unreachable'
        ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400'
        : 'bg-muted text-muted-foreground'
  const healthLabel =
    health === 'checking' ? 'Checking…' : health === 'healthy' ? 'Online' : 'Offline'

  // Derive live stats from the graph
  const totalNodes = graphProp?.nodes.length ?? null
  const failedCount = graphProp?.nodes.filter((n) => n.status === 'failed').length ?? 0
  const degradedCount = graphProp?.nodes.filter((n) => n.status === 'degraded').length ?? 0
  const healthyCount = (totalNodes ?? 0) - failedCount - degradedCount
  const incidentCount = failedCount + degradedCount
  const rootCause = graphProp?.meta.root_cause_candidate ?? null

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {/* Backend health */}
      <Card className="shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">Backend API</span>
            <span className="relative flex size-2.5">
              {health === 'healthy' && (
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              )}
              <span
                className={cn(
                  'relative inline-flex size-2.5 rounded-full',
                  health === 'healthy' ? 'bg-emerald-500' : health === 'unreachable' ? 'bg-red-500' : 'bg-muted-foreground',
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

      {/* Active Incidents */}
      <Card className="shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">Active Incidents</span>
            {incidentCount > 0 && (
              <span className="relative flex size-2.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-red-400 opacity-60" />
                <span className="relative inline-flex size-2.5 rounded-full bg-red-500" />
              </span>
            )}
          </div>
          <div className="flex items-baseline gap-2">
            <span className="whitespace-nowrap font-mono text-3xl font-semibold tracking-tight">
              {graphProp === null || graphProp === undefined ? '—' : incidentCount}
            </span>
            <span className="text-sm text-balance text-muted-foreground">
              {incidentCount === 0 ? 'All clear' : `${failedCount} failed, ${degradedCount} degraded`}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Healthy Services */}
      <Card className="shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">Healthy Nodes</span>
            {totalNodes !== null && failedCount === 0 && (
              <span className="relative flex size-2.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500" />
              </span>
            )}
          </div>
          <div className="flex items-baseline gap-2">
            <span className="whitespace-nowrap font-mono text-3xl font-semibold tracking-tight">
              {totalNodes === null ? '—' : `${healthyCount} / ${totalNodes}`}
            </span>
            <span className="text-sm text-balance text-muted-foreground">
              {totalNodes === null ? 'Inject a scenario' : failedCount === 0 ? 'All operational' : 'Cascade active'}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Root Cause */}
      <Card className={cn(
        'shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md',
        rootCause ? 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/10' : '',
      )}>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">Root Cause</span>
            {rootCause && (
              <span className="relative flex size-2.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-red-400 opacity-60" />
                <span className="relative inline-flex size-2.5 rounded-full bg-red-500" />
              </span>
            )}
          </div>
          <div className="flex items-baseline gap-2">
            <span className={cn(
              'whitespace-nowrap font-mono text-xl font-semibold tracking-tight',
              rootCause ? 'text-red-700 dark:text-red-400' : '',
            )}>
              {rootCause ?? (graphProp ? 'None' : '—')}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
