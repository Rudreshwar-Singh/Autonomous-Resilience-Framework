'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, Wifi, WifiOff, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { type GraphPayload, HEALTHY_SCENARIO, PAYMENT_TIMEOUT_SCENARIO, fetchTopology, injectFaultScenario } from '@/lib/api'
import { cn } from '@/lib/utils'

// ── Node layout positions (normalised 0-100 coordinate space) ─────────────────
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  Client: { x: 50, y: 8 },
  'API-Gateway': { x: 50, y: 28 },
  'Checkout-Service': { x: 30, y: 50 },
  'Payment-Gateway': { x: 30, y: 72 },
  'Payment-DB': { x: 30, y: 92 },
  // Fallback positions for unknown nodes
  default: { x: 70, y: 50 },
}

function getPos(id: string) {
  return NODE_POSITIONS[id] ?? { x: 70 + Math.random() * 20, y: 30 + Math.random() * 40 }
}

// ── Status colour mappings ─────────────────────────────────────────────────────
const nodeStatusFill: Record<string, string> = {
  success: 'fill-emerald-500',
  healthy: 'fill-emerald-500',
  degraded: 'fill-amber-400',
  failed: 'fill-red-500',
}
const nodeStatusStroke: Record<string, string> = {
  success: 'stroke-emerald-500',
  healthy: 'stroke-emerald-500',
  degraded: 'stroke-amber-400',
  failed: 'stroke-red-500',
}
const nodeRingColor: Record<string, string> = {
  success: 'rgba(16,185,129,0.25)',
  healthy: 'rgba(16,185,129,0.25)',
  degraded: 'rgba(251,191,36,0.3)',
  failed: 'rgba(239,68,68,0.3)',
}

export function TopologyGraph({ onGraphUpdate }: { onGraphUpdate?: (g: GraphPayload | null) => void }) {
  const [graph, setGraph] = useState<GraphPayload | null>(null)
  const [injecting, setInjecting] = useState(false)
  const [recovering, setRecovering] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadTopology = useCallback(async () => {
    const data = await fetchTopology()
    setGraph(data)
    if (data) setLastUpdated(new Date())
    onGraphUpdate?.(data)
  }, [onGraphUpdate])

  useEffect(() => {
    void loadTopology()
    intervalRef.current = setInterval(loadTopology, 5000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [loadTopology])

  async function handleInjectFault() {
    setInjecting(true)
    setError(null)
    try {
      const result = await injectFaultScenario(PAYMENT_TIMEOUT_SCENARIO)
      setGraph(result)
      setLastUpdated(new Date())
      onGraphUpdate?.(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Injection failed')
    } finally {
      setInjecting(false)
    }
  }

  async function handleSimulateRecovery() {
    setRecovering(true)
    setError(null)
    try {
      const result = await injectFaultScenario(HEALTHY_SCENARIO)
      setGraph(result)
      setLastUpdated(new Date())
      onGraphUpdate?.(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recovery failed')
    } finally {
      setRecovering(false)
    }
  }

  const failedCount = graph?.nodes.filter((n) => n.status === 'failed').length ?? 0
  const degradedCount = graph?.nodes.filter((n) => n.status === 'degraded').length ?? 0
  const rootCause = graph?.meta.root_cause_candidate

  return (
    <Card className="shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <CardTitle>Service Dependency Topology</CardTitle>
          <CardDescription>
            Live map of service-to-service dependencies — auto-refreshes every 5 seconds.
          </CardDescription>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {graph ? (
            <Badge variant="secondary" className="gap-1.5">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
              </span>
              {graph.nodes.length} nodes
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1.5 text-muted-foreground">
              <WifiOff className="size-3" />
              No data
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Inject Fault Button — the main demo trigger */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="destructive"
            onClick={handleInjectFault}
            disabled={injecting || recovering}
            className="gap-2"
            id="inject-fault-btn"
          >
            {injecting ? (
              <><Loader2 className="size-4 animate-spin" />Injecting…</>
            ) : (
              <><Zap className="size-4" />Inject Payment Cascade Failure</>
            )}
          </Button>
          <Button
            size="sm"
            onClick={handleSimulateRecovery}
            disabled={injecting || recovering}
            className="gap-2 bg-emerald-600 text-white hover:bg-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-600"
            id="simulate-recovery-btn"
          >
            {recovering ? (
              <><Loader2 className="size-4 animate-spin" />Recovering…</>
            ) : (
              <><CheckCircle2 className="size-4" />Simulate System Recovery</>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void loadTopology()}
            className="gap-2"
            id="refresh-topology-btn"
          >
            <RefreshCw className="size-4" />
            Refresh
          </Button>
          {lastUpdated && (
            <span className="ml-auto text-xs text-muted-foreground">
              <Wifi className="mr-1 inline size-3 text-emerald-500" />
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Alert banners */}
        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-700 dark:bg-red-950/30 dark:text-red-400">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            {error}
          </div>
        )}
        {rootCause && (
          <div className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm dark:border-red-700 dark:bg-red-950/30">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-500" />
            <div>
              <span className="font-semibold text-red-700 dark:text-red-400">Root Cause Detected: </span>
              <span className="font-mono text-red-700 dark:text-red-400">{rootCause}</span>
              {(graph?.meta.blast_radius?.length ?? 0) > 0 && (
                <span className="text-red-600 dark:text-red-500"> — blast radius: {graph!.meta.blast_radius.join(', ')}</span>
              )}
            </div>
          </div>
        )}

        {/* Graph canvas */}
        <div className="relative w-full overflow-hidden rounded-lg border bg-muted/30">
          <div
            aria-hidden
            className="absolute inset-0 opacity-[0.4] [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:32px_32px]"
          />

          {!graph ? (
            <div className="flex h-72 flex-col items-center justify-center gap-2 text-muted-foreground md:h-96">
              <WifiOff className="size-8 opacity-30" />
              <p className="text-sm">No topology data yet.</p>
              <p className="text-xs">Click &ldquo;Inject Payment Cascade Failure&rdquo; above to begin the demo.</p>
            </div>
          ) : (
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="xMidYMid meet"
              className="relative h-72 w-full md:h-96"
              role="img"
              aria-label="Live service dependency topology graph"
            >
              {/* Edges */}
              {graph.edges.map((edge) => {
                const from = getPos(edge.source)
                const to = getPos(edge.target)
                return (
                  <line
                    key={`${edge.source}-${edge.target}`}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    className="stroke-border"
                    strokeWidth={0.5}
                    strokeDasharray={edge.source === graph.meta.root_cause_candidate ? '1.5 0.8' : undefined}
                  />
                )
              })}

              {/* Nodes */}
              {graph.nodes.map((node) => {
                const pos = getPos(node.id)
                const fill = nodeStatusFill[node.status] ?? 'fill-muted-foreground'
                const stroke = nodeStatusStroke[node.status] ?? 'stroke-muted-foreground'
                const isRoot = node.id === graph.meta.root_cause_candidate
                return (
                  <g key={node.id}>
                    {/* Outer pulse ring */}
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={isRoot ? 8 : 5.5}
                      fill={nodeRingColor[node.status] ?? 'transparent'}
                      className={isRoot ? 'animate-pulse' : ''}
                    />
                    {/* Core dot */}
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={3.2}
                      className={cn(fill, stroke, 'opacity-95')}
                      strokeWidth={0.6}
                    />
                    {/* Label */}
                    <text
                      x={pos.x}
                      y={pos.y + 9}
                      textAnchor="middle"
                      className="fill-muted-foreground font-sans"
                      style={{ fontSize: '3px' }}
                    >
                      {node.id}
                    </text>
                    {/* Status label for failed/degraded */}
                    {(node.status === 'failed' || node.status === 'degraded') && (
                      <text
                        x={pos.x}
                        y={pos.y - 7}
                        textAnchor="middle"
                        className={node.status === 'failed' ? 'fill-red-500' : 'fill-amber-500'}
                        style={{ fontSize: '2.8px', fontWeight: 'bold' }}
                      >
                        {node.status === 'failed' ? '✖ FAILED' : '⚠ DEGRADED'}
                      </text>
                    )}
                  </g>
                )
              })}
            </svg>
          )}
        </div>

        {/* Status legend */}
        {graph && (
          <>
            <Separator />
            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-emerald-500" />
                Healthy ({graph.nodes.filter((n) => n.status === 'success').length})
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-amber-400" />
                Degraded ({degradedCount})
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-red-500" />
                Failed ({failedCount})
              </span>
              {failedCount === 0 && degradedCount === 0 && (
                <span className="ml-auto flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-3.5" />
                  All services healthy
                </span>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
