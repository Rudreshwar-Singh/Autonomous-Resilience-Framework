import { CalendarClock, Download, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

export function DashboardHeader() {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-semibold tracking-tight">Observability Overview</h2>
          <Badge variant="secondary" className="gap-1.5">
            <span className="size-1.5 rounded-full bg-success" />
            Live
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Real-time health, telemetry, and autonomous remediation across your fleet.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Tooltip>
          <TooltipTrigger
            render={
              <span className="inline-flex">
                <Button variant="outline" size="sm" className="transition-colors">
                  <CalendarClock data-icon="inline-start" />
                  Last 24 hours
                </Button>
              </span>
            }
          />
          <TooltipContent>Change the time range</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger
            render={
              <span className="inline-flex">
                <Button variant="outline" size="sm" className="transition-colors">
                  <RefreshCw data-icon="inline-start" />
                  Refresh
                </Button>
              </span>
            }
          />
          <TooltipContent>Refresh dashboard data</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger
            render={
              <span className="inline-flex">
                <Button size="sm" className="transition-colors">
                  <Download data-icon="inline-start" />
                  Export
                </Button>
              </span>
            }
          />
          <TooltipContent>Export as CSV report</TooltipContent>
        </Tooltip>
      </div>
    </div>
  )
}
