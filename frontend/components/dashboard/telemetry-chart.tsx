'use client'

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import { telemetrySeries } from '@/lib/mock-data'

const chartConfig = {
  requests: { label: 'Requests', color: 'var(--chart-1)' },
  errors: { label: 'Errors', color: 'var(--chart-4)' },
} satisfies ChartConfig

export function TelemetryChart() {
  return (
    <Card className="h-full shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader>
        <CardTitle>Request Throughput &amp; Errors</CardTitle>
        <CardDescription>Fleet-wide traffic over the last 24 hours</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="aspect-auto h-[280px] w-full">
          <AreaChart data={telemetrySeries} margin={{ left: 4, right: 8, top: 8 }}>
            <defs>
              <linearGradient id="fillRequests" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-requests)" stopOpacity={0.35} />
                <stop offset="95%" stopColor="var(--color-requests)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="fillErrors" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-errors)" stopOpacity={0.35} />
                <stop offset="95%" stopColor="var(--color-errors)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={24}
            />
            <YAxis tickLine={false} axisLine={false} tickMargin={8} width={40} />
            <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="line" />} />
            <Area
              dataKey="requests"
              type="monotone"
              fill="url(#fillRequests)"
              stroke="var(--color-requests)"
              strokeWidth={2}
            />
            <Area
              dataKey="errors"
              type="monotone"
              fill="url(#fillErrors)"
              stroke="var(--color-errors)"
              strokeWidth={2}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
