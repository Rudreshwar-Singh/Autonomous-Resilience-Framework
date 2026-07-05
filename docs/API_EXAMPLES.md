# API Examples — Autonomous Resilience Framework

Complete, copy-pasteable request/response examples for every active API endpoint.
All examples assume the server is running locally at `http://127.0.0.1:8000`.

> **Note:** Start the server with:
> ```bash
> uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
> ```

---

## Table of Contents

- [Health Domain](#health-domain)
- [Telemetry Domain](#telemetry-domain)
- [Analysis Domain — Graph Topology (Phase 6)](#analysis-domain--graph-topology-phase-6)
- [Incident Domain](#incident-domain)
- [Agent Domain](#agent-domain)

---

## Health Domain

### `GET /healthz` — Application Liveness Probe

```bash
curl http://127.0.0.1:8000/healthz
```

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "service": "Autonomous Resilience Framework",
  "version": "0.1.0",
  "timestamp": "2026-07-05T07:00:00.000+00:00"
}
```

---

### `GET /api/v1/health/` — Dependency-Aware Health Check

```bash
curl http://127.0.0.1:8000/api/v1/health/
```

**Response `200 OK`:**
```json
{
  "status": "placeholder",
  "service": "health"
}
```

---

## Telemetry Domain

### `POST /api/v1/telemetry/` — Ingest a Telemetry Event

Publishes a validated `TelemetryEvent` to the Kafka `system-telemetry` topic.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/telemetry/ \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-07-05T12:00:00Z",
    "service_name": "payment-svc",
    "level": "ERROR",
    "message": "Database connection pool exhausted — retrying in 5s"
  }'
```

**Response `202 Accepted`:**
```json
{
  "status": "accepted",
  "event_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Validation Error `422 Unprocessable Entity`** (missing required field):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/telemetry/ \
  -H "Content-Type: application/json" \
  -d '{"service_name": "payment-svc"}'
```
```json
{
  "detail": [
    { "type": "missing", "loc": ["body", "timestamp"], "msg": "Field required" },
    { "type": "missing", "loc": ["body", "level"],     "msg": "Field required" },
    { "type": "missing", "loc": ["body", "message"],   "msg": "Field required" }
  ]
}
```

---

## Analysis Domain — Graph Topology (Phase 6)

These endpoints are the core of the **Phase 6 NetworkX Brain**.

---

### `POST /api/v1/graph/analyze` — Build Dependency Graph from Trace Logs

Accepts a batch of `TraceEvent` records, runs the `GraphAnalyzer`, and returns
a complete `GraphPayload` (nodes + edges + root-cause metadata).

**Scenario: Cascading failure — User-DB timeout propagates to Auth-Service and API-Gateway.**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/graph/analyze \
  -H "Content-Type: application/json" \
  -d '[
    {
      "trace_id": "req-9912",
      "timestamp": "2026-07-05T12:00:01Z",
      "source_node": "Client",
      "target_node": "API-Gateway",
      "status": "success"
    },
    {
      "trace_id": "req-9912",
      "timestamp": "2026-07-05T12:00:02Z",
      "source_node": "API-Gateway",
      "target_node": "Auth-Service",
      "status": "success"
    },
    {
      "trace_id": "req-9912",
      "timestamp": "2026-07-05T12:00:03Z",
      "source_node": "Auth-Service",
      "target_node": "User-DB",
      "status": "failed",
      "error_metadata": {
        "error_code": "DB_TIMEOUT_ERROR",
        "message": "Connection timeout while querying User-DB replica",
        "latency_ms": 30042.7,
        "extra": { "db_host": "user-db-primary:5432", "retry_count": 3 }
      }
    },
    {
      "trace_id": "req-9912",
      "timestamp": "2026-07-05T12:00:04Z",
      "source_node": "API-Gateway",
      "target_node": "Auth-Service",
      "status": "failed",
      "error_metadata": {
        "error_code": "500_INTERNAL_SERVER_ERROR",
        "message": "Dependency User-DB failed to respond within SLO",
        "latency_ms": 30100.2,
        "extra": { "upstream_error": "DB_TIMEOUT_ERROR" }
      }
    }
  ]'
```

**Response `200 OK`:**
```json
{
  "nodes": [
    {
      "id": "Client",
      "status": "success",
      "error_metadata": null,
      "call_count": 0,
      "failure_count": 0
    },
    {
      "id": "API-Gateway",
      "status": "success",
      "error_metadata": null,
      "call_count": 1,
      "failure_count": 0
    },
    {
      "id": "Auth-Service",
      "status": "failed",
      "error_metadata": {
        "error_code": "500_INTERNAL_SERVER_ERROR",
        "message": "Dependency User-DB failed to respond within SLO",
        "latency_ms": 30100.2,
        "extra": { "upstream_error": "DB_TIMEOUT_ERROR" }
      },
      "call_count": 2,
      "failure_count": 1
    },
    {
      "id": "User-DB",
      "status": "failed",
      "error_metadata": {
        "error_code": "DB_TIMEOUT_ERROR",
        "message": "Connection timeout while querying User-DB replica",
        "latency_ms": 30042.7,
        "extra": { "db_host": "user-db-primary:5432", "retry_count": 3 }
      },
      "call_count": 1,
      "failure_count": 1
    }
  ],
  "edges": [
    { "source": "Client",       "target": "API-Gateway",  "weight": 1 },
    { "source": "API-Gateway",  "target": "Auth-Service", "weight": 2 },
    { "source": "Auth-Service", "target": "User-DB",      "weight": 1 }
  ],
  "meta": {
    "total_nodes": 4,
    "total_edges": 3,
    "failed_node_count": 2,
    "root_cause_candidate": "User-DB",
    "blast_radius": ["Client", "API-Gateway", "Auth-Service"]
  }
}
```

**Error `400 Bad Request`** (empty event list):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/graph/analyze \
  -H "Content-Type: application/json" \
  -d '[]'
```
```json
{
  "detail": "Event list must not be empty. Provide at least one TraceEvent."
}
```

---

### `GET /api/v1/graph/topology` — Retrieve Cached Topology Graph

Returns the last graph computed by `POST /analyze`. Designed for frontend polling
(e.g., React dashboard refreshing every 5 seconds).

```bash
curl http://127.0.0.1:8000/api/v1/graph/topology
```

**Response `200 OK`:** *(same schema as POST /analyze response above)*

**Error `404 Not Found`** (no analysis run yet in this session):
```json
{
  "detail": "No graph topology is available yet. POST to /api/v1/graph/analyze first to build the dependency graph."
}
```

---

### `GET /api/v1/graph/health` — Analysis Domain Health Probe

```bash
curl http://127.0.0.1:8000/api/v1/graph/health
```

**Response `200 OK`** (before any /analyze call):
```json
{
  "status": "operational",
  "domain": "analysis",
  "graph_cache_available": false
}
```

**Response `200 OK`** (after a successful /analyze call):
```json
{
  "status": "operational",
  "domain": "analysis",
  "graph_cache_available": true
}
```

---

## Incident Domain

### `GET /api/v1/incident/` — List Active Incidents

```bash
curl http://127.0.0.1:8000/api/v1/incident/
```

**Response `200 OK`** *(Phase 2 placeholder — business logic in Phase 7)*:
```json
{
  "status": "placeholder",
  "service": "incident"
}
```

---

### `POST /api/v1/incident/` — Manually Open an Incident

```bash
curl -X POST http://127.0.0.1:8000/api/v1/incident/
```

**Response `201 Created`** *(Phase 2 placeholder)*:
```json
{
  "status": "placeholder",
  "service": "incident"
}
```

---

## Agent Domain

### `GET /api/v1/agent/` — List Agent Actions

```bash
curl http://127.0.0.1:8000/api/v1/agent/
```

**Response `200 OK`** *(Phase 2 placeholder — AI logic in Phase 7)*:
```json
{
  "status": "placeholder",
  "service": "agent"
}
```

---

## TraceEvent Schema Reference (Phase 6)

Full schema for `POST /api/v1/graph/analyze` request body items:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trace_id` | `string` | ✅ | Groups all hops in one logical request |
| `timestamp` | `datetime` | ✅ | UTC ISO-8601 datetime of the call |
| `source_node` | `string` | ✅ | Calling service name (e.g. `"API-Gateway"`) |
| `target_node` | `string` | ✅ | Receiving service name (e.g. `"Auth-Service"`) |
| `status` | `"success"` \| `"failed"` \| `"degraded"` | ✅ | Outcome of this hop |
| `event_id` | `UUID` | ❌ | Auto-generated if omitted |
| `error_metadata` | `ErrorMetadata` | ❌ | Required when `status != "success"` |

**ErrorMetadata sub-schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_code` | `string` | ✅ | Machine-readable error code |
| `message` | `string` | ✅ | Human-readable explanation |
| `latency_ms` | `float` | ❌ | Round-trip latency in milliseconds |
| `extra` | `dict` | ❌ | Arbitrary additional metadata |
