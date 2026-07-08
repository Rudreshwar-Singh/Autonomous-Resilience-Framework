/**
 * API Service Layer — lib/api.ts
 * ================================
 * Single source of truth for all backend HTTP communication.
 * Updated Phase 6+7: Added topology, fault injection, and remediation endpoints.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

// ── Response Types ─────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  service: string
  version: string
  timestamp: string
}

export interface ErrorMetadata {
  error_code: string
  message: string
  latency_ms?: number | null
  extra?: Record<string, unknown> | null
}

export interface GraphNode {
  id: string
  status: 'success' | 'failed' | 'degraded'
  error_metadata: ErrorMetadata | null
  call_count: number
  failure_count: number
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface GraphMeta {
  total_nodes: number
  total_edges: number
  failed_node_count: number
  root_cause_candidate: string | null
  blast_radius: string[]
}

export interface GraphPayload {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta: GraphMeta
}

export interface RemediationPlan {
  root_cause: string
  impacted_nodes: string[]
  suggested_action: string
  target_service: string
}

export interface TraceEvent {
  trace_id: string
  timestamp: string
  source_node: string
  target_node: string
  status: 'success' | 'failed' | 'degraded'
  error_metadata?: ErrorMetadata | null
}

// The payment cascade scenario (same as data/fault_scenarios/payment_timeout.json)
export const PAYMENT_TIMEOUT_SCENARIO: TraceEvent[] = [
  {
    trace_id: 'trace-pay-9001',
    timestamp: new Date().toISOString(),
    source_node: 'Client',
    target_node: 'API-Gateway',
    status: 'success',
    error_metadata: null,
  },
  {
    trace_id: 'trace-pay-9001',
    timestamp: new Date(Date.now() + 50).toISOString(),
    source_node: 'API-Gateway',
    target_node: 'Checkout-Service',
    status: 'success',
    error_metadata: null,
  },
  {
    trace_id: 'trace-pay-9001',
    timestamp: new Date(Date.now() + 120).toISOString(),
    source_node: 'Checkout-Service',
    target_node: 'Payment-Gateway',
    status: 'degraded',
    error_metadata: {
      error_code: 'UPSTREAM_TIMEOUT',
      message: 'Payment-Gateway upstream call exceeded SLO threshold — response time 4800ms (SLO: 500ms)',
      latency_ms: 4800,
      extra: { http_status: 504, retry_count: 3 },
    },
  },
  {
    trace_id: 'trace-pay-9001',
    timestamp: new Date(Date.now() + 5021).toISOString(),
    source_node: 'Payment-Gateway',
    target_node: 'Payment-DB',
    status: 'failed',
    error_metadata: {
      error_code: 'DB_TIMEOUT_ERROR',
      message: 'Connection pool exhausted — Payment-DB failed to respond within 5000ms. All 20 connections timed out.',
      latency_ms: 5000,
      extra: { pool_size: 20, active_connections: 20, queue_depth: 87, db_host: 'payment-db.internal' },
    },
  },
  {
    trace_id: 'trace-pay-9001',
    timestamp: new Date(Date.now() + 5025).toISOString(),
    source_node: 'Checkout-Service',
    target_node: 'API-Gateway',
    status: 'failed',
    error_metadata: {
      error_code: '500_INTERNAL_SERVER_ERROR',
      message: 'Checkout-Service returned HTTP 500 after Payment-Gateway cascade failure. Transaction ID txn-8812-XYZ aborted.',
      latency_ms: 4910,
      extra: { http_status: 500, transaction_id: 'txn-8812-XYZ', rollback_triggered: true },
    },
  },
]

export const HEALTHY_SCENARIO: TraceEvent[] = [
  {
    trace_id: 'trace-healthy-001',
    timestamp: new Date().toISOString(),
    source_node: 'Client',
    target_node: 'API-Gateway',
    status: 'success',
    error_metadata: null,
  },
  {
    trace_id: 'trace-healthy-001',
    timestamp: new Date(Date.now() + 50).toISOString(),
    source_node: 'API-Gateway',
    target_node: 'Checkout-Service',
    status: 'success',
    error_metadata: null,
  },
  {
    trace_id: 'trace-healthy-001',
    timestamp: new Date(Date.now() + 100).toISOString(),
    source_node: 'Checkout-Service',
    target_node: 'Payment-Gateway',
    status: 'success',
    error_metadata: null,
  },
  {
    trace_id: 'trace-healthy-001',
    timestamp: new Date(Date.now() + 150).toISOString(),
    source_node: 'Payment-Gateway',
    target_node: 'Payment-DB',
    status: 'success',
    error_metadata: null,
  }
]

// ── API Functions ──────────────────────────────────────────────────────────────

export async function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/healthz`, { cache: 'no-store', signal })
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json() as Promise<HealthResponse>
}

export async function fetchTopology(): Promise<GraphPayload | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/graph/topology`, { cache: 'no-store' })
    if (res.status === 404) return null // No graph yet — expected before first injection
    if (!res.ok) throw new Error(`Topology fetch failed: ${res.status}`)
    return res.json() as Promise<GraphPayload>
  } catch {
    return null
  }
}

export async function injectFaultScenario(events: TraceEvent[]): Promise<GraphPayload> {
  const res = await fetch(`${BASE_URL}/api/v1/graph/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(events),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Fault injection failed (${res.status}): ${err}`)
  }
  return res.json() as Promise<GraphPayload>
}

export async function triggerRemediate(graphPayload: GraphPayload): Promise<RemediationPlan> {
  const res = await fetch(`${BASE_URL}/api/v1/agent/remediate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ graph_payload: graphPayload, error_traceback: null }),
  })
  const data = (await res.json()) as RemediationPlan | { detail: string }
  if (!res.ok) {
    throw new Error(`Remediation failed (${res.status}): ${'detail' in data ? data.detail : 'Unknown error'}`)
  }
  return data as RemediationPlan
}
