import { Filter, Maximize2, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { topologyEdges, topologyNodes } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

const topologyControls = [
  { icon: ZoomIn, label: 'Zoom In', hint: 'Zoom into the topology' },
  { icon: ZoomOut, label: 'Zoom Out', hint: 'Zoom out of the topology' },
  { icon: RotateCcw, label: 'Reset View', hint: 'Reset zoom and position' },
  { icon: Filter, label: 'Filter', hint: 'Filter nodes by status' },
] as const

const nodeStatusFill = {
  healthy: 'fill-success',
  degraded: 'fill-warning',
  critical: 'fill-critical',
} as const

const nodeStatusStroke = {
  healthy: 'stroke-success',
  degraded: 'stroke-warning',
  critical: 'stroke-critical',
} as const

function getNode(id: string) {
  return topologyNodes.find((n) => n.id === id)
}

export function TopologyGraph() {
  return (
    <Card className="shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <CardTitle>Service Dependency Topology</CardTitle>
          <CardDescription>
            Live map of service-to-service dependencies and traffic flow across the fleet.
          </CardDescription>
        </div>
        <Badge variant="secondary" className="shrink-0">
          {topologyNodes.length} nodes
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="relative w-full overflow-hidden rounded-lg border bg-muted/30">
          {/* subtle grid background */}
          <div
            aria-hidden
            className="absolute inset-0 opacity-[0.4] [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:32px_32px]"
          />
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="xMidYMid meet"
            className="relative h-72 w-full md:h-96"
            role="img"
            aria-label="Service dependency topology graph placeholder"
          >
            {topologyEdges.map((edge) => {
              const from = getNode(edge.from)
              const to = getNode(edge.to)
              if (!from || !to) return null
              return (
                <line
                  key={`${edge.from}-${edge.to}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  className="stroke-border"
                  strokeWidth={0.4}
                />
              )
            })}
            {topologyNodes.map((node) => (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={3.2}
                  className={cn(nodeStatusFill[node.status], nodeStatusStroke[node.status], 'opacity-90')}
                  strokeWidth={0.6}
                />
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={5.5}
                  className={cn(nodeStatusStroke[node.status], 'fill-none opacity-30')}
                  strokeWidth={0.5}
                />
                <text
                  x={node.x}
                  y={node.y + 9}
                  textAnchor="middle"
                  className="fill-muted-foreground font-sans"
                  style={{ fontSize: '3px' }}
                >
                  {node.label}
                </text>
              </g>
            ))}
          </svg>
        </div>

        <Separator />

        {/* Reserved space for future graph controls (non-functional) */}
        <div className="flex flex-wrap items-center gap-2">
          {topologyControls.map((control) => {
            const Icon = control.icon
            return (
              <Tooltip key={control.label}>
                <TooltipTrigger
                  render={
                    <span className="inline-flex">
                      <Button variant="outline" size="sm" disabled>
                        <Icon data-icon="inline-start" />
                        {control.label}
                      </Button>
                    </span>
                  }
                />
                <TooltipContent>{control.hint}</TooltipContent>
              </Tooltip>
            )
          })}
          <Tooltip>
            <TooltipTrigger
              render={
                <span className="ml-auto inline-flex">
                  <Button variant="outline" size="sm" disabled>
                    <Maximize2 data-icon="inline-start" />
                    Fullscreen
                  </Button>
                </span>
              }
            />
            <TooltipContent>Expand to fullscreen</TooltipContent>
          </Tooltip>
        </div>
      </CardContent>
    </Card>
  )
}
