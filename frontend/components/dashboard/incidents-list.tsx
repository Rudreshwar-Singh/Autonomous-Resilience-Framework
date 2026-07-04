import { ShieldCheck, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { incidents } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

const severityStyles: Record<string, string> = {
  sev1: 'bg-critical/10 text-critical',
  sev2: 'bg-warning/10 text-warning',
  sev3: 'bg-muted text-muted-foreground',
}

const statusLabels: Record<string, string> = {
  open: 'Open',
  'auto-healing': 'Auto-healing',
  resolved: 'Resolved',
}

export function IncidentsList() {
  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>Active Incidents</CardTitle>
          <CardDescription>Prioritized by severity and impact</CardDescription>
        </div>
        <Badge variant="secondary" className="shrink-0">
          {incidents.length}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {incidents.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-10 text-center">
            <span className="flex size-10 items-center justify-center rounded-full bg-success/10 text-success">
              <ShieldCheck className="size-5" />
            </span>
            <p className="text-sm font-medium">No active incidents</p>
            <p className="max-w-[28ch] text-xs text-muted-foreground text-pretty">
              All services are operating within their expected thresholds.
            </p>
          </div>
        ) : (
          incidents.map((inc) => (
          <div
            key={inc.id}
            className="flex flex-col gap-2 rounded-lg border border-border p-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-border/80 hover:bg-accent/40 hover:shadow-sm"
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'rounded px-1.5 py-0.5 text-xs font-semibold uppercase',
                  severityStyles[inc.severity],
                )}
              >
                {inc.severity}
              </span>
              <span className="font-mono text-xs text-muted-foreground">{inc.id}</span>
              <span className="ml-auto text-xs text-muted-foreground">{inc.startedAt}</span>
            </div>
            <p className="text-sm font-medium leading-snug text-pretty">{inc.title}</p>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {inc.service}
              </Badge>
              <Badge
                variant={inc.status === 'resolved' ? 'secondary' : 'default'}
                className="text-xs"
              >
                {statusLabels[inc.status]}
              </Badge>
              {inc.autoRemediated && (
                <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-primary">
                  <Sparkles className="size-3" />
                  AI
                </span>
              )}
            </div>
          </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}
