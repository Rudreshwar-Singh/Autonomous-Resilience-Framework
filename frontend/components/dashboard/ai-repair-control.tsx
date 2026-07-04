'use client'

import { useState } from 'react'
import { Activity, Crosshair, Lightbulb, Loader2, ShieldCheck, Sparkles, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { triggerAgent } from '@/lib/api'
import { repairAnalysis } from '@/lib/mock-data'

const analysisItems = [
  { icon: Activity, label: 'Root Cause', value: repairAnalysis.rootCause, mono: false },
  { icon: Lightbulb, label: 'Suggested Action', value: repairAnalysis.suggestedAction, mono: false },
  { icon: Crosshair, label: 'Target Service', value: repairAnalysis.targetService, mono: true },
] as const

export function AiRepairControl() {
  const [state, setState] = useState<'ready' | 'running' | 'done' | 'error'>('ready')
  const [agentResponse, setAgentResponse] = useState<string | null>(null)
  const running = state === 'running'

  async function handleExecute() {
    setState('running')
    setAgentResponse(null)
    try {
      const data = await triggerAgent({
        target_service: repairAnalysis.targetService,
        action: repairAnalysis.suggestedAction,
      })
      setState('done')
      setAgentResponse(`Agent acknowledged: ${JSON.stringify(data)}`)
      // Auto-reset to 'ready' after 5 seconds so the operator can re-trigger
      // without needing to refresh the page.
      setTimeout(() => setState('ready'), 5_000)
    } catch (err) {
      setState('error')
      setAgentResponse(
        err instanceof Error ? err.message : 'Network error — is the backend running?',
      )
    }
  }

  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Sparkles className="size-4" />
          </span>
          <div className="flex flex-col gap-1.5">
            <CardTitle>AI Autonomous Repair Control</CardTitle>
            <CardDescription>Review the diagnosis, then authorize remediation.</CardDescription>
          </div>
        </div>
        <Badge
          variant="secondary"
          className="shrink-0 gap-1.5 border border-success/30 bg-success/10 text-success"
        >
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-success" />
          </span>
          {running ? 'AI Agent Working' : 'AI Agent Ready'}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Diagnosis card */}
          <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4">
            {analysisItems.map((item, i) => {
              const Icon = item.icon
              return (
                <div key={item.label}>
                  {i > 0 && <Separator className="mb-3" />}
                  <div className="flex items-start gap-2.5">
                    <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        {item.label}
                      </p>
                      <p
                        className={
                          item.mono
                            ? 'mt-0.5 font-mono text-sm text-foreground'
                            : 'mt-0.5 text-sm leading-snug text-foreground text-pretty'
                        }
                      >
                        {item.value}
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
            <Separator className="mb-0.5" />
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Confidence Score
                  </p>
                  <span className="font-mono text-sm font-semibold text-success">
                    {repairAnalysis.confidence}%
                  </span>
                </div>
                <Progress value={repairAnalysis.confidence} className="mt-2 h-1.5" />
              </div>
            </div>
          </div>

          {/* Execute panel */}
          <div className="flex flex-col justify-center gap-4 rounded-lg border border-critical/20 bg-critical/5 p-4">
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium text-foreground">Autonomous Remediation</p>
              <p className="text-xs text-muted-foreground text-pretty">
                Applies the recommended fix to{' '}
                <span className="font-mono text-foreground">{repairAnalysis.targetService}</span>. This is
                a guarded, high-impact action.
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
                      className="h-14 w-full bg-critical text-base font-semibold text-critical-foreground shadow-sm transition-all duration-200 hover:bg-critical/90 hover:shadow-md active:scale-[0.99] focus-visible:ring-critical/40"
                    >
                      {running ? (
                        <>
                          <Loader2 data-icon="inline-start" className="animate-spin" />
                          Executing Remediation…
                        </>
                      ) : state === 'done' ? (
                        <>
                          <ShieldCheck data-icon="inline-start" />
                          Remediation Dispatched
                        </>
                      ) : state === 'error' ? (
                        <>
                          <Zap data-icon="inline-start" />
                          Retry AI Remediation
                        </>
                      ) : (
                        <>
                          <Zap data-icon="inline-start" />
                          Execute AI Remediation
                        </>
                      )}
                    </Button>
                  </span>
                }
              />
              <TooltipContent>
                {running ? 'Remediation in progress' : `Apply the AI fix to ${repairAnalysis.targetService}`}
              </TooltipContent>
            </Tooltip>
            <p className="text-center text-xs text-muted-foreground">
              Requires operator authorization · fully audited
            </p>
            {agentResponse && (
              <p
                className={`mt-1 rounded-md border px-3 py-2 font-mono text-xs ${
                  state === 'error'
                    ? 'border-critical/30 bg-critical/5 text-critical'
                    : 'border-success/30 bg-success/5 text-success'
                }`}
              >
                {agentResponse}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
