'use client'

import { useEffect, useState } from 'react'
import { ShieldCheck, Sparkles, WifiOff } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { type GraphNode, type GraphPayload, fetchTopology } from '@/lib/api'
import { cn } from '@/lib/utils'

const severityFromStatus: Record<string, string> = {
  failed: 'sev1',
  degraded: 'sev2',
}

const severityStyles: Record<string, string> = {
  sev1: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400',
  sev2: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  sev3: 'bg-muted text-muted-foreground',
}

function incidentTitle(node: GraphNode, isRootCause: boolean): string {
  if (isRootCause) {
    return `Root cause: ${node.error_metadata?.error_code ?? 'Unknown error'} on ${node.id}`
  }
  if (node.status === 'failed') {
    return `Cascading failure detected on ${node.id}`
  }
  return `Performance degradation on ${node.id} — SLO breach`
}

export function IncidentsList({ graphProp, rootCause }: { graphProp?: GraphPayload | null; rootCause?: string | null }) {
  const [graph, setGraph] = useState<GraphPayload | null>(null)
  const [liveRootCause, setLiveRootCause] = useState<string | null>(null)

  useEffect(() => {
    if (graphProp !== undefined) {
      setGraph(graphProp)
      setLiveRootCause(rootCause ?? graphProp?.meta.root_cause_candidate ?? null)
      return
    }
    async function load() {
      const data = await fetchTopology()
      setGraph(data)
      setLiveRootCause(data?.meta.root_cause_candidate ?? null)
    }
    void load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [graphProp, rootCause])

  const impactedNodes = graph?.nodes.filter(
    (n) => n.status === 'failed' || n.status === 'degraded',
  ) ?? []

  const activeRoot = liveRootCause

  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>Active Incidents</CardTitle>
          <CardDescription>
            {graph ? 'Derived from live NetworkX fault graph' : 'Waiting for graph data…'}
          </CardDescription>
        </div>
        <Badge
          variant="secondary"
          className={cn(
            'shrink-0',
            impactedNodes.length > 0
              ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400'
              : '',
          )}
        >
          {impactedNodes.length}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!graph || impactedNodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-10 text-center">
            {!graph ? (
              <>
                <WifiOff className="size-6 opacity-30 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No graph data yet.</p>
                <p className="max-w-[28ch] text-xs text-muted-foreground text-pretty">Inject a fault scenario to see incidents here.</p>
              </>
            ) : (
              <>
                <span className="flex size-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                  <ShieldCheck className="size-5" />
                </span>
                <p className="text-sm font-medium">No active incidents</p>
                <p className="max-w-[28ch] text-xs text-muted-foreground text-pretty">
                  All services are operating within expected thresholds.
                </p>
              </>
            )}
          </div>
        ) : (
          impactedNodes
            .sort((a, b) => {
              if (a.id === activeRoot) return -1
              if (b.id === activeRoot) return 1
              return a.status === 'failed' ? -1 : 1
            })
            .map((node) => {
              const isRoot = node.id === activeRoot
              const sev = severityFromStatus[node.status] ?? 'sev3'
              return (
                <div
                  key={node.id}
                  className={cn(
                    'flex flex-col gap-2 rounded-lg border p-3 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm',
                    isRoot
                      ? 'border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/20'
                      : 'border-border hover:bg-accent/40',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 text-xs font-semibold uppercase',
                        severityStyles[sev],
                      )}
                    >
                      {sev}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">{node.id}</span>
                    {isRoot && (
                      <Badge className="ml-auto gap-1 bg-red-600 text-xs text-white">
                        <Sparkles className="size-3" />
                        Root Cause
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm font-medium leading-snug text-pretty">
                    {incidentTitle(node, isRoot)}
                  </p>
                  {node.error_metadata?.message && (
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {node.error_metadata.message}
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {node.status}
                    </Badge>
                    <Badge variant="default" className={cn('text-xs', node.status === 'failed' ? 'bg-red-600' : 'bg-amber-500')}>
                      {node.status === 'failed' ? 'Open' : 'Degraded'}
                    </Badge>
                    {isRoot && (
                      <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-primary">
                        <Sparkles className="size-3" />
                        AI Detected
                      </span>
                    )}
                  </div>
                </div>
              )
            })
        )}
      </CardContent>
    </Card>
  )
}
