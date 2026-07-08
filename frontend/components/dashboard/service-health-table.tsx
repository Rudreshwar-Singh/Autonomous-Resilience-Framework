'use client'

import { useEffect, useState } from 'react'
import { WifiOff } from 'lucide-react'
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
import { type GraphNode, type GraphPayload, fetchTopology } from '@/lib/api'
import { cn } from '@/lib/utils'

const statusConfig: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  success: {
    label: 'Healthy',
    bg: 'bg-emerald-100 dark:bg-emerald-950/40',
    text: 'text-emerald-700 dark:text-emerald-400',
    dot: 'bg-emerald-500',
  },
  degraded: {
    label: 'Degraded',
    bg: 'bg-amber-100 dark:bg-amber-950/40',
    text: 'text-amber-700 dark:text-amber-400',
    dot: 'bg-amber-400',
  },
  failed: {
    label: 'Failed',
    bg: 'bg-red-100 dark:bg-red-950/40',
    text: 'text-red-700 dark:text-red-400',
    dot: 'bg-red-500',
  },
}

function NodeRow({ node }: { node: GraphNode }) {
  const cfg = statusConfig[node.status] ?? statusConfig.success
  const errorRate = node.call_count > 0
    ? ((node.failure_count / node.call_count) * 100).toFixed(1)
    : '0.0'

  return (
    <TableRow className="transition-colors">
      <TableCell className="pl-6">
        <div className="flex flex-col">
          <span className="font-mono font-medium">{node.id}</span>
          {node.error_metadata?.error_code && (
            <span className="text-xs text-muted-foreground">{node.error_metadata.error_code}</span>
          )}
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
      <TableCell className="text-right font-mono text-sm">
        {node.error_metadata?.latency_ms != null
          ? `${node.error_metadata.latency_ms}ms`
          : '—'}
      </TableCell>
      <TableCell
        className={cn(
          'text-right font-mono text-sm',
          Number(errorRate) >= 50
            ? 'text-red-600 dark:text-red-400'
            : Number(errorRate) > 0
              ? 'text-amber-600 dark:text-amber-400'
              : 'text-muted-foreground',
        )}
      >
        {errorRate}%
      </TableCell>
      <TableCell className="hidden pr-6 text-right font-mono text-sm text-muted-foreground sm:table-cell">
        {node.call_count} calls
      </TableCell>
    </TableRow>
  )
}

export function ServiceHealthTable({ graphProp }: { graphProp?: GraphPayload | null }) {
  const [graph, setGraph] = useState<GraphPayload | null>(null)

  useEffect(() => {
    if (graphProp !== undefined) {
      setGraph(graphProp)
      return
    }
    async function load() {
      const data = await fetchTopology()
      setGraph(data)
    }
    void load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [graphProp])

  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>Service Health</CardTitle>
          <CardDescription>
            {graph ? 'Live status from NetworkX dependency graph' : 'Waiting for graph data…'}
          </CardDescription>
        </div>
        <Badge variant="secondary" className="shrink-0">
          {graph ? `${graph.nodes.length} nodes` : '—'}
        </Badge>
      </CardHeader>
      <CardContent className="px-0">
        {!graph ? (
          <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-muted-foreground">
            <WifiOff className="size-6 opacity-30" />
            <p className="text-sm">No graph data yet.</p>
            <p className="text-xs">Inject a fault scenario to see live service health here.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-6">Service Node</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Latency</TableHead>
                  <TableHead className="text-right">Error %</TableHead>
                  <TableHead className="hidden pr-6 text-right sm:table-cell">Call Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* Sort: failed first, degraded second, success last */}
                {[...graph.nodes]
                  .sort((a, b) => {
                    const order = { failed: 0, degraded: 1, success: 2 }
                    return (order[a.status] ?? 3) - (order[b.status] ?? 3)
                  })
                  .map((node) => (
                    <NodeRow key={node.id} node={node} />
                  ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
