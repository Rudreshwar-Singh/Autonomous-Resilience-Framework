export type ServiceStatus = 'healthy' | 'degraded' | 'critical'

export interface Service {
  id: string
  name: string
  namespace: string
  status: ServiceStatus
  latencyMs: number
  errorRate: number
  requestsPerMin: number
  uptime: number
}

export const services: Service[] = [
  { id: 'svc-01', name: 'api-gateway', namespace: 'edge', status: 'healthy', latencyMs: 42, errorRate: 0.02, requestsPerMin: 18420, uptime: 99.99 },
  { id: 'svc-02', name: 'auth-service', namespace: 'identity', status: 'healthy', latencyMs: 68, errorRate: 0.05, requestsPerMin: 9210, uptime: 99.98 },
  { id: 'svc-03', name: 'payments', namespace: 'commerce', status: 'degraded', latencyMs: 214, errorRate: 1.8, requestsPerMin: 3120, uptime: 99.82 },
  { id: 'svc-04', name: 'inventory', namespace: 'commerce', status: 'healthy', latencyMs: 55, errorRate: 0.09, requestsPerMin: 4870, uptime: 99.95 },
  { id: 'svc-05', name: 'notifications', namespace: 'messaging', status: 'critical', latencyMs: 892, errorRate: 12.4, requestsPerMin: 640, uptime: 97.4 },
  { id: 'svc-06', name: 'search-indexer', namespace: 'data', status: 'healthy', latencyMs: 121, errorRate: 0.3, requestsPerMin: 2210, uptime: 99.91 },
  { id: 'svc-07', name: 'recommendation', namespace: 'ml', status: 'degraded', latencyMs: 340, errorRate: 2.1, requestsPerMin: 1580, uptime: 99.6 },
  { id: 'svc-08', name: 'user-profile', namespace: 'identity', status: 'healthy', latencyMs: 47, errorRate: 0.04, requestsPerMin: 6120, uptime: 99.97 },
]

export interface MetricPoint {
  time: string
  requests: number
  errors: number
  latency: number
}

export const telemetrySeries: MetricPoint[] = Array.from({ length: 24 }, (_, i) => {
  const hour = i.toString().padStart(2, '0') + ':00'
  const base = 12000 + Math.sin(i / 3) * 3800 + i * 120
  const errors = Math.max(20, 260 + Math.sin(i / 2) * 180 + (i > 16 && i < 20 ? 420 : 0))
  const latency = 60 + Math.sin(i / 4) * 22 + (i > 16 && i < 20 ? 140 : 0)
  return {
    time: hour,
    requests: Math.round(base),
    errors: Math.round(errors),
    latency: Math.round(latency),
  }
})

export interface Incident {
  id: string
  title: string
  service: string
  severity: 'sev1' | 'sev2' | 'sev3'
  status: 'open' | 'auto-healing' | 'resolved'
  startedAt: string
  autoRemediated: boolean
}

export const incidents: Incident[] = [
  { id: 'INC-2041', title: 'Elevated 5xx rate on notifications queue', service: 'notifications', severity: 'sev1', status: 'auto-healing', startedAt: '4m ago', autoRemediated: true },
  { id: 'INC-2038', title: 'Payment latency above SLO threshold', service: 'payments', severity: 'sev2', status: 'open', startedAt: '22m ago', autoRemediated: false },
  { id: 'INC-2035', title: 'Recommendation model timeout spike', service: 'recommendation', severity: 'sev2', status: 'auto-healing', startedAt: '38m ago', autoRemediated: true },
  { id: 'INC-2030', title: 'Auth token refresh backlog', service: 'auth-service', severity: 'sev3', status: 'resolved', startedAt: '2h ago', autoRemediated: true },
  { id: 'INC-2027', title: 'Search indexer memory pressure', service: 'search-indexer', severity: 'sev3', status: 'resolved', startedAt: '5h ago', autoRemediated: true },
]

export interface AgentAction {
  id: string
  action: string
  target: string
  confidence: number
  time: string
  outcome: 'applied' | 'monitoring' | 'suggested'
}

export const agentActions: AgentAction[] = [
  { id: 'act-1', action: 'Scaled replicas 4 → 8', target: 'notifications', confidence: 96, time: '4m ago', outcome: 'applied' },
  { id: 'act-2', action: 'Enabled circuit breaker', target: 'payments', confidence: 89, time: '19m ago', outcome: 'monitoring' },
  { id: 'act-3', action: 'Rerouted traffic to us-west-2', target: 'recommendation', confidence: 92, time: '35m ago', outcome: 'applied' },
  { id: 'act-4', action: 'Restart unhealthy pod group', target: 'notifications', confidence: 78, time: '1h ago', outcome: 'suggested' },
  { id: 'act-5', action: 'Increased connection pool', target: 'auth-service', confidence: 84, time: '2h ago', outcome: 'applied' },
]

export interface StatCard {
  label: string
  value: string
  caption?: string
  indicator?: 'success' | 'warning' | 'critical'
  badge?: string
}

export const stats: StatCard[] = [
  { label: 'Global Health', value: '99.9%', indicator: 'success' },
  { label: 'Healthy Services', value: '12 / 12', caption: 'All systems operational' },
  { label: 'Active Incidents', value: '0', badge: 'Stable' },
  { label: 'Kafka Queue', value: '0', caption: 'Pending Messages' },
]

export type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'SUCCESS'

export interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  service: string
  message: string
}

export const telemetryLogs: LogEntry[] = [
  { id: 'log-01', timestamp: '14:02:11.482', level: 'INFO', service: 'api-gateway', message: 'Ingress request routed to auth-service (p50 42ms)' },
  { id: 'log-02', timestamp: '14:02:11.913', level: 'DEBUG', service: 'auth-service', message: 'JWT verified for principal usr_8f21 · scope=read:all' },
  { id: 'log-03', timestamp: '14:02:12.334', level: 'WARN', service: 'payments', message: 'Latency 214ms exceeds SLO threshold (200ms)' },
  { id: 'log-04', timestamp: '14:02:12.771', level: 'ERROR', service: 'notifications', message: '5xx rate spike detected · 12.4% over trailing 60s window' },
  { id: 'log-05', timestamp: '14:02:13.109', level: 'INFO', service: 'autoheal-agent', message: 'Anomaly correlated to notifications queue backpressure' },
  { id: 'log-06', timestamp: '14:02:13.540', level: 'SUCCESS', service: 'autoheal-agent', message: 'Remediation plan generated · confidence 96%' },
  { id: 'log-07', timestamp: '14:02:14.002', level: 'INFO', service: 'inventory', message: 'Reservation batch committed · 4870 rpm sustained' },
  { id: 'log-08', timestamp: '14:02:14.418', level: 'DEBUG', service: 'kafka', message: 'Consumer group lag=0 across 12 partitions' },
  { id: 'log-09', timestamp: '14:02:14.860', level: 'WARN', service: 'recommendation', message: 'Model inference timeout retry 1/3 · us-east-1' },
  { id: 'log-10', timestamp: '14:02:15.221', level: 'SUCCESS', service: 'autoheal-agent', message: 'Scaled notifications replicas 4 → 8 · healthy' },
  { id: 'log-11', timestamp: '14:02:15.688', level: 'INFO', service: 'search-indexer', message: 'Segment merge complete · heap 61% utilized' },
  { id: 'log-12', timestamp: '14:02:16.045', level: 'DEBUG', service: 'postgres', message: 'Checkpoint flushed · WAL 128MB · repl lag 12ms' },
]

export const logLineTemplates: Array<Pick<LogEntry, 'level' | 'service' | 'message'>> = [
  { level: 'INFO', service: 'api-gateway', message: 'Ingress request routed · p50 41ms' },
  { level: 'DEBUG', service: 'auth-service', message: 'Session token refreshed · ttl 3600s' },
  { level: 'WARN', service: 'payments', message: 'Latency drift +18ms over baseline' },
  { level: 'SUCCESS', service: 'autoheal-agent', message: 'Circuit breaker recovered · traffic restored' },
  { level: 'INFO', service: 'inventory', message: 'Cache warm-up complete · hit ratio 98.2%' },
  { level: 'ERROR', service: 'notifications', message: 'Dead-letter enqueue · retrying delivery' },
  { level: 'DEBUG', service: 'kafka', message: 'Rebalance complete · 12 partitions assigned' },
  { level: 'INFO', service: 'recommendation', message: 'Model warm · batch inference 128 items' },
  { level: 'SUCCESS', service: 'autoheal-agent', message: 'Health probe green across fleet' },
  { level: 'DEBUG', service: 'postgres', message: 'Vacuum autotune complete · bloat 2.1%' },
]

export interface RepairAnalysis {
  rootCause: string
  suggestedAction: string
  targetService: string
  confidence: number
}

export const repairAnalysis: RepairAnalysis = {
  rootCause: 'Queue backpressure on notifications consumer group driving elevated 5xx rate',
  suggestedAction: 'Scale replicas 4 → 8 and enable adaptive circuit breaker',
  targetService: 'notifications',
  confidence: 96,
}

export interface TopologyNode {
  id: string
  label: string
  x: number
  y: number
  status: ServiceStatus
}

export interface TopologyEdge {
  from: string
  to: string
}

export const topologyNodes: TopologyNode[] = [
  { id: 'gateway', label: 'API Gateway', x: 50, y: 12, status: 'healthy' },
  { id: 'auth', label: 'Auth', x: 20, y: 40, status: 'healthy' },
  { id: 'payments', label: 'Payments', x: 50, y: 42, status: 'degraded' },
  { id: 'inventory', label: 'Inventory', x: 80, y: 40, status: 'healthy' },
  { id: 'kafka', label: 'Kafka', x: 35, y: 72, status: 'healthy' },
  { id: 'notifications', label: 'Notifications', x: 65, y: 72, status: 'critical' },
  { id: 'db', label: 'Postgres', x: 50, y: 92, status: 'healthy' },
]

export const topologyEdges: TopologyEdge[] = [
  { from: 'gateway', to: 'auth' },
  { from: 'gateway', to: 'payments' },
  { from: 'gateway', to: 'inventory' },
  { from: 'auth', to: 'kafka' },
  { from: 'payments', to: 'kafka' },
  { from: 'payments', to: 'notifications' },
  { from: 'inventory', to: 'notifications' },
  { from: 'kafka', to: 'db' },
  { from: 'notifications', to: 'db' },
]
