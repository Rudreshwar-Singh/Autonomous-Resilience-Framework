'use client'

import { useEffect, useRef, useState } from 'react'
import { Radio } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { type LogEntry, type LogLevel, logLineTemplates, telemetryLogs } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

const levelMeta: Record<LogLevel, { label: string; text: string; dot: string }> = {
  INFO: { label: 'INFO', text: 'text-sky-400', dot: 'bg-sky-400' },
  DEBUG: { label: 'DBUG', text: 'text-muted-foreground', dot: 'bg-muted-foreground' },
  WARN: { label: 'WARN', text: 'text-warning', dot: 'bg-warning' },
  ERROR: { label: 'ERRR', text: 'text-critical', dot: 'bg-critical' },
  SUCCESS: { label: 'OK  ', text: 'text-success', dot: 'bg-success' },
}

function nextTimestamp(prev: string) {
  const [h, m, s] = prev.split(':')
  const base = new Date()
  base.setHours(Number(h), Number(m), Math.floor(Number(s)))
  base.setMilliseconds((Number(s) % 1) * 1000)
  base.setTime(base.getTime() + 400 + Math.floor(Math.random() * 900))
  const hh = String(base.getHours()).padStart(2, '0')
  const mm = String(base.getMinutes()).padStart(2, '0')
  const ss = String(base.getSeconds()).padStart(2, '0')
  const ms = String(base.getMilliseconds()).padStart(3, '0')
  return `${hh}:${mm}:${ss}.${ms}`
}

export function LiveTelemetryLogs() {
  const [logs, setLogs] = useState<LogEntry[]>(telemetryLogs)
  const scrollRef = useRef<HTMLDivElement>(null)
  const counter = useRef(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setLogs((prev) => {
        const template = logLineTemplates[counter.current % logLineTemplates.length]
        counter.current += 1
        const last = prev[prev.length - 1]
        const entry: LogEntry = {
          id: `live-${counter.current}`,
          timestamp: nextTimestamp(last?.timestamp ?? '14:02:16.045'),
          ...template,
        }
        // keep a rolling buffer so memory stays bounded
        return [...prev.slice(-80), entry]
      })
    }, 2200)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [logs])

  return (
    <Card className="flex h-full flex-col overflow-hidden shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <CardTitle className="flex items-center gap-2">
            <Radio className="size-4 text-success" />
            Live Telemetry Logs
          </CardTitle>
          <CardDescription>Streaming events across the observability pipeline.</CardDescription>
        </div>
        <Badge variant="secondary" className="shrink-0 gap-1.5">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-success" />
          </span>
          Live
        </Badge>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col p-0">
        <div className="flex items-center gap-1.5 border-y bg-muted/40 px-4 py-2">
          <span className="size-2.5 rounded-full bg-critical/70" />
          <span className="size-2.5 rounded-full bg-warning/70" />
          <span className="size-2.5 rounded-full bg-success/70" />
          <span className="ml-2 font-mono text-xs text-muted-foreground">autoheal@fleet: ~ /var/log/telemetry</span>
        </div>
        <div
          ref={scrollRef}
          className="min-h-72 flex-1 overflow-y-auto bg-background/60 px-4 py-3 font-mono text-xs leading-relaxed"
          role="log"
          aria-live="polite"
          aria-label="Live telemetry log stream"
        >
          {logs.map((log) => {
            const meta = levelMeta[log.level]
            return (
              <p key={log.id} className="py-0.5 text-foreground/90">
                <span className="text-muted-foreground/70">{log.timestamp}</span>{' '}
                <span className={cn('font-semibold', meta.text)}>{meta.label.trim()}</span>{' '}
                <span className="text-primary/80">[{log.service}]</span>{' '}
                <span>{log.message}</span>
              </p>
            )
          })}
          <p className="flex items-center gap-2 py-0.5 text-success">
            <span className="text-muted-foreground/70">{'>'}</span>
            <span className="inline-block h-3.5 w-2 animate-pulse bg-success" aria-hidden />
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
