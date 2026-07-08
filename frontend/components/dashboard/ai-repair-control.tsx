'use client'

import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, Crosshair, Lightbulb, Loader2, ShieldCheck, Sparkles, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { type GraphPayload, type RemediationPlan, fetchTopology, triggerRemediate } from '@/lib/api'

export function AiRepairControl({ graphProp }: { graphProp?: GraphPayload | null }) {
  const [graph, setGraph] = useState<GraphPayload | null>(null)
  const [state, setState] = useState<'idle' | 'loading-graph' | 'ready' | 'running' | 'done' | 'error'>('loading-graph')
  const [plan, setPlan] = useState<RemediationPlan | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Load graph from prop (passed from topology) or fetch directly
  useEffect(() => {
    if (graphProp !== undefined) {
      setGraph(graphProp)
      setState(graphProp ? 'ready' : 'idle')
      return
    }
    async function load() {
      setState('loading-graph')
      const data = await fetchTopology()
      setGraph(data)
      setState(data ? 'ready' : 'idle')
    }
    void load()
  }, [graphProp])

  const running = state === 'running'

  // Derive analysis from graph
  const rootCause = graph?.meta.root_cause_candidate ?? null
  const failedNodes = graph?.nodes.filter((n) => n.status === 'failed').map((n) => n.id) ?? []
  const degradedNodes = graph?.nodes.filter((n) => n.status === 'degraded').map((n) => n.id) ?? []
  const allImpacted = [...new Set([...failedNodes, ...degradedNodes])]
  const isHealthy = graph !== null && allImpacted.length === 0

  async function handleExecute() {
    if (!graph) return
    setState('running')
    setPlan(null)
    setErrorMsg(null)
    try {
      const result = await triggerRemediate(graph)
      setPlan(result)
      setState('done')
    } catch (err) {
      setState('error')
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return (
    <Card className="shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Sparkles className="size-4" />
          </span>
          <div className="flex flex-col gap-1.5">
            <CardTitle>AI Autonomous Repair Control</CardTitle>
            <CardDescription>Real-time Gemini diagnosis — click Execute to remediate.</CardDescription>
          </div>
        </div>
        <Badge
          variant="secondary"
          className={`shrink-0 gap-1.5 border ${
            state === 'done'
              ? 'border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400'
              : state === 'error'
                ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950/30 dark:text-red-400'
                : running
                  ? 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-400'
                  : 'border-emerald-300/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
          }`}
        >
          <span className="relative flex size-2">
            <span className={`absolute inline-flex size-full animate-ping rounded-full opacity-75 ${running ? 'bg-amber-400' : 'bg-emerald-400'}`} />
            <span className={`relative inline-flex size-2 rounded-full ${running ? 'bg-amber-400' : 'bg-emerald-500'}`} />
          </span>
          {running ? 'AI Agent Working…' : state === 'done' ? 'Plan Applied' : state === 'idle' ? 'Waiting for Graph' : state === 'loading-graph' ? 'Loading…' : 'AI Agent Ready'}
        </Badge>
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        {(state === 'idle' || state === 'loading-graph' || isHealthy) ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-10 text-center text-muted-foreground">
            {state === 'loading-graph' ? (
              <><Loader2 className="size-6 animate-spin" /><p className="text-sm">Loading graph data…</p></>
            ) : isHealthy ? (
              <>
                <ShieldCheck className="size-6 text-emerald-500 opacity-80" />
                <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">All Systems Operational</p>
                <p className="max-w-[32ch] text-xs text-pretty">No active incidents detected. AI Remediation is standing by.</p>
              </>
            ) : (
              <>
                <AlertTriangle className="size-6 opacity-40" />
                <p className="text-sm font-medium">No fault graph available.</p>
                <p className="max-w-[32ch] text-xs text-pretty">Inject the payment cascade failure using the topology card above, then the AI diagnosis will appear here automatically.</p>
              </>
            )}
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Diagnosis card — from live graph */}
            <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4">
              <div>
                <div className="flex items-start gap-2.5">
                  <Activity className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Root Cause Candidate</p>
                    <p className="mt-0.5 font-mono text-sm font-semibold text-foreground">
                      {plan?.root_cause ?? (rootCause ? rootCause : 'Analyzing…')}
                    </p>
                  </div>
                </div>
              </div>
              <Separator />
              <div>
                <div className="flex items-start gap-2.5">
                  <Lightbulb className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Suggested Action</p>
                    <p className="mt-0.5 text-sm leading-snug text-foreground text-pretty">
                      {plan?.suggested_action ?? `${failedNodes.length} failed node(s) detected. Execute AI remediation for a detailed plan.`}
                    </p>
                  </div>
                </div>
              </div>
              <Separator />
              <div>
                <div className="flex items-start gap-2.5">
                  <Crosshair className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Target Service</p>
                    <p className="mt-0.5 font-mono text-sm text-foreground">{plan?.target_service ?? rootCause ?? '—'}</p>
                  </div>
                </div>
              </div>
              {plan && (
                <>
                  <Separator />
                  <div className="flex items-start gap-2.5">
                    <ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-500" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Impacted Services</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {plan.impacted_nodes.map((n) => (
                          <span key={n} className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-xs text-red-700 dark:bg-red-950/40 dark:text-red-400">{n}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}
              <Separator className="mb-0.5" />
              <div className="flex items-start gap-2.5">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-500" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Failure Scope</p>
                    <span className="font-mono text-sm font-semibold text-red-600">
                      {failedNodes.length + degradedNodes.length} / {graph?.nodes.length ?? 0}
                    </span>
                  </div>
                  <Progress
                    value={graph ? ((failedNodes.length + degradedNodes.length) / graph.nodes.length) * 100 : 0}
                    className="mt-2 h-1.5"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    {allImpacted.length > 0 ? `Affected: ${allImpacted.join(', ')}` : 'No impacted nodes detected.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Execute panel */}
            <div className="flex flex-col justify-center gap-4 rounded-lg border border-red-200 bg-red-500/5 p-4 dark:border-red-800">
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium text-foreground">Autonomous Remediation</p>
                <p className="text-xs text-muted-foreground text-pretty">
                  Sends the live graph to <span className="font-mono text-foreground">Gemini AI</span> and returns a validated remediation plan.
                </p>
              </div>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <span className="inline-flex w-full">
                      <Button
                        size="lg"
                        onClick={handleExecute}
                        disabled={running}
                        id="execute-remediation-btn"
                        className="h-14 w-full bg-red-600 text-base font-semibold text-white shadow-sm transition-all duration-200 hover:bg-red-700 hover:shadow-md active:scale-[0.99]"
                      >
                        {running ? (
                          <><Loader2 className="mr-2 size-5 animate-spin" />Asking Gemini AI…</>
                        ) : state === 'done' ? (
                          <><ShieldCheck className="mr-2 size-5" />Plan Applied ✓</>
                        ) : state === 'error' ? (
                          <><Zap className="mr-2 size-5" />Retry AI Remediation</>
                        ) : (
                          <><Zap className="mr-2 size-5" />Execute AI Remediation</>
                        )}
                      </Button>
                    </span>
                  }
                />
                <TooltipContent>
                  {running ? 'Gemini is analyzing the fault graph…' : 'Send fault graph to Gemini for root cause analysis'}
                </TooltipContent>
              </Tooltip>

              <p className="text-center text-xs text-muted-foreground">
                Powered by Google Gemini Flash · Pydantic-validated output
              </p>

              {errorMsg && (
                <p className="mt-1 rounded-md border border-red-300 bg-red-50 px-3 py-2 font-mono text-xs text-red-700 dark:border-red-700 dark:bg-red-950/30 dark:text-red-400">
                  {errorMsg}
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
