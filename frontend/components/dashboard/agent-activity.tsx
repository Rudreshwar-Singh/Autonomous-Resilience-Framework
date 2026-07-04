import { Bot, CheckCircle2, Eye, Lightbulb, Inbox } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { agentActions } from '@/lib/mock-data'

const outcomeMeta = {
  applied: { icon: CheckCircle2, label: 'Applied', className: 'text-success' },
  monitoring: { icon: Eye, label: 'Monitoring', className: 'text-warning' },
  suggested: { icon: Lightbulb, label: 'Suggested', className: 'text-muted-foreground' },
} as const

export function AgentActivity() {
  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader>
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Bot className="size-4" />
          </span>
          <div>
            <CardTitle>AI Agent Activity</CardTitle>
            <CardDescription>Autonomous remediation timeline</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {agentActions.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-10 text-center">
            <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <Inbox className="size-5" />
            </span>
            <p className="text-sm font-medium">No agent activity yet</p>
            <p className="max-w-[28ch] text-xs text-muted-foreground text-pretty">
              Autonomous remediation actions will appear here as the agent responds to incidents.
            </p>
          </div>
        ) : (
          agentActions.map((action) => {
          const meta = outcomeMeta[action.outcome]
          const Icon = meta.icon
          return (
            <div
              key={action.id}
              className="flex flex-col gap-1.5 rounded-md p-2 transition-colors hover:bg-accent/40"
            >
              <div className="flex items-start gap-2">
                <Icon className={`mt-0.5 size-4 shrink-0 ${meta.className}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-snug text-pretty">{action.action}</p>
                  <p className="text-xs text-muted-foreground">
                    {action.target} · {action.time} · {meta.label}
                  </p>
                </div>
                <span className="font-mono text-xs text-muted-foreground">{action.confidence}%</span>
              </div>
              <Progress value={action.confidence} className="h-1" />
            </div>
          )
          })
        )}
      </CardContent>
    </Card>
  )
}
