/**
 * API Service Layer — lib/api.ts
 * ================================
 * Single source of truth for all backend HTTP communication.
 *
 * WHY THIS FILE EXISTS:
 *   Hardcoding `http://127.0.0.1:8000` directly in components violates the
 *   DRY principle and makes environment changes (Docker, staging, production)
 *   require hunting through every component file. This module centralizes all
 *   fetch logic so that:
 *   1. The base URL is controlled by a single environment variable.
 *   2. All API calls have consistent error handling and type safety.
 *   3. Future phases can swap `fetch` for a typed SDK (e.g., openapi-fetch)
 *      in one place without touching any component.
 *
 * USAGE:
 *   import { fetchHealth, triggerAgent } from '@/lib/api'
 *
 * ENVIRONMENT VARIABLE:
 *   Set NEXT_PUBLIC_API_URL in `.env.local` for local dev.
 *   For Docker, override it in docker-compose.yml or a .env.production file.
 */

// ── Base URL ───────────────────────────────────────────────────────────────────
// NEXT_PUBLIC_ prefix is required by Next.js to expose env vars to the browser.
// Falls back to the local FastAPI dev server if the variable is not set.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

// ── Response Types ─────────────────────────────────────────────────────────────

/** Shape of the response from the /healthz liveness probe. */
export interface HealthResponse {
  status: string
  service: string
  version: string
  timestamp: string
}

/** Shape of the request body sent to the agent trigger endpoint. */
export interface AgentTriggerRequest {
  target_service: string
  action: string
}

/** Generic shape of the agent trigger placeholder response. */
export type AgentTriggerResponse = Record<string, unknown>


// ── API Functions ──────────────────────────────────────────────────────────────

/**
 * Fetches the backend liveness probe at /healthz.
 *
 * Used by StatCards to display a real-time "Backend API: Online/Offline" badge.
 * Passes an AbortSignal so the caller can cancel the request on component
 * unmount, preventing React state-update-on-unmounted-component warnings.
 *
 * @param signal - An AbortSignal from an AbortController to cancel the request.
 * @returns A resolved HealthResponse object.
 * @throws Error if the network request fails or the response is not OK.
 */
export async function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/healthz`, {
    cache: 'no-store', // Always fetch fresh — this is a liveness probe.
    signal,
  })
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`)
  }
  return res.json() as Promise<HealthResponse>
}


/**
 * Sends a POST request to dispatch the AI Remediation Agent.
 *
 * This is a "fire-and-forget" trigger — the backend accepts the job (202) and
 * runs it asynchronously. The component displays the acknowledgement payload.
 *
 * @param payload - The target service and suggested action for remediation.
 * @returns The raw acknowledgement JSON from the agent router.
 * @throws Error if the network request fails or the backend returns an error.
 */
export async function triggerAgent(
  payload: AgentTriggerRequest,
): Promise<AgentTriggerResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/agent/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = (await res.json()) as AgentTriggerResponse
  if (!res.ok) {
    throw new Error(`Agent trigger failed (${res.status}): ${JSON.stringify(data)}`)
  }
  return data
}
