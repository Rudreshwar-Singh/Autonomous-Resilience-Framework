import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { services } from '@/lib/mock-data'
import { statusConfig } from '@/lib/status'
import { cn } from '@/lib/utils'

export function ServiceHealthTable() {
  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>Service Health</CardTitle>
          <CardDescription>Live status across monitored microservices</CardDescription>
        </div>
        <Badge variant="secondary" className="shrink-0">
          {services.length} services
        </Badge>
      </CardHeader>
      <CardContent className="px-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Service</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Latency</TableHead>
                <TableHead className="text-right">Error %</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Req/min</TableHead>
                <TableHead className="pr-6 text-right">Uptime</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {services.map((svc) => {
                const cfg = statusConfig[svc.status]
                return (
                  <TableRow key={svc.id} className="transition-colors">
                    <TableCell className="pl-6">
                      <div className="flex flex-col">
                        <span className="font-medium">{svc.name}</span>
                        <span className="text-xs text-muted-foreground">{svc.namespace}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
                          cfg.bg,
                          cfg.text,
                        )}
                      >
                        <span className={cn('size-1.5 rounded-full', cfg.dot)} />
                        {cfg.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">{svc.latencyMs}ms</TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-mono text-sm',
                        svc.errorRate >= 5
                          ? 'text-critical'
                          : svc.errorRate >= 1
                            ? 'text-warning'
                            : 'text-muted-foreground',
                      )}
                    >
                      {svc.errorRate.toFixed(2)}
                    </TableCell>
                    <TableCell className="hidden text-right font-mono text-sm text-muted-foreground sm:table-cell">
                      {svc.requestsPerMin.toLocaleString()}
                    </TableCell>
                    <TableCell className="pr-6 text-right font-mono text-sm">{svc.uptime}%</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
