import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const cardShell = 'h-full shadow-sm'

function HeaderSkeleton() {
  return (
    <CardHeader className="flex flex-row items-start justify-between gap-4">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-44" />
        <Skeleton className="h-3 w-60 max-w-full" />
      </div>
      <Skeleton className="h-6 w-16 rounded-full" />
    </CardHeader>
  )
}

export function StatCardsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="shadow-sm">
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="size-2.5 rounded-full" />
            </div>
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-3 w-28" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function TopologySkeleton() {
  return (
    <Card className={cardShell}>
      <HeaderSkeleton />
      <CardContent className="flex flex-col gap-4">
        <Skeleton className="h-72 w-full rounded-lg md:h-96" />
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-24 rounded-md" />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function AiRepairSkeleton() {
  return (
    <Card className={cardShell}>
      <HeaderSkeleton />
      <CardContent className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-4 rounded-lg border bg-muted/30 p-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex flex-col gap-2">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-4 w-full" />
            </div>
          ))}
        </div>
        <div className="flex flex-col justify-center gap-4 rounded-lg border p-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-14 w-full rounded-md" />
          <Skeleton className="mx-auto h-3 w-48" />
        </div>
      </CardContent>
    </Card>
  )
}

export function TelemetryLogsSkeleton() {
  return (
    <Card className={cardShell}>
      <HeaderSkeleton />
      <CardContent className="p-0">
        <div className="border-y bg-muted/40 px-4 py-2">
          <Skeleton className="h-3 w-56" />
        </div>
        <div className="flex flex-col gap-2.5 px-4 py-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-3" style={{ width: `${60 + ((i * 7) % 35)}%` }} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function ChartSkeleton() {
  return (
    <Card className={cardShell}>
      <HeaderSkeleton />
      <CardContent>
        <Skeleton className="h-[280px] w-full rounded-lg" />
      </CardContent>
    </Card>
  )
}

export function IncidentsSkeleton() {
  return (
    <Card className={cardShell}>
      <HeaderSkeleton />
      <CardContent className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2 rounded-lg border p-3">
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-12 rounded" />
              <Skeleton className="h-3 w-16" />
              <Skeleton className="ml-auto h-3 w-14" />
            </div>
            <Skeleton className="h-4 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function ServiceHealthSkeleton() {
  return (
    <Card className={cardShell}>
      <HeaderSkeleton />
      <CardContent className="flex flex-col gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="hidden h-4 w-12 sm:block" />
            <Skeleton className="h-4 w-12" />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function AgentActivitySkeleton() {
  return (
    <Card className={cardShell}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Skeleton className="size-7 rounded-md" />
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="flex items-start gap-2">
              <Skeleton className="mt-0.5 size-4 rounded-full" />
              <div className="flex flex-1 flex-col gap-1.5">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-40" />
              </div>
              <Skeleton className="h-3 w-8" />
            </div>
            <Skeleton className="h-1 w-full" />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
