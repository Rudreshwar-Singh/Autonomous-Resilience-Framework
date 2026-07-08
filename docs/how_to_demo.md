# How to Demo the Framework
## Autonomous Resilience Framework — 3-Minute Live Technical Demo

> **Prerequisite:** Stack running via `docker-compose up`, Next.js dashboard open in browser

---

## PHASE 1 — THE HOOK (45 seconds)

**Introduction**

"Every large-scale distributed system fails. That is not a question of *if* — it is a question of *when*. And when it does, the average enterprise takes **34 minutes** to detect the incident and another 60 minutes to resolve it. That is MTTR — Mean Time To Resolution — and it is the single most expensive metric in platform engineering. Downtime at the scale of companies like Amazon or Flipkart costs roughly $100,000 **per minute**.

The reason MTTR is so high is not lack of tooling. Datadog and Grafana will tell you *something* is broken. The problem is they cannot tell you *why* — or what to fix first. An on-call engineer still has to mentally trace 200 microservice logs at 3 AM to find the root cause.

What I built here eliminates that. This is the **Autonomous Resilience Framework**: a system that watches your microservice topology in real time, uses graph-based root cause analysis to instantly pinpoint the broken node, and then uses a Gemini LLM to generate a deterministic, step-by-step remediation plan — automatically, before your on-call engineer even picks up their phone."

---

## PHASE 2 — THE INCIDENT (75 seconds)

**Action: Switch to terminal and navigate to the project root.**

"Let me show you a real scenario. I have a simulated payment microservice chain: Client hits the API Gateway, which calls Checkout Service, which calls Payment Gateway, which queries the Payment Database. A classic e-commerce critical path.

I am going to inject a cascading failure now."

**Action: Run the curl command or Python ingest script:**

```bash
# Inject the fault scenario
curl -X POST http://localhost:8000/api/v1/telemetry/trace/batch \
     -H "Content-Type: application/json" \
     -d @data/fault_scenarios/payment_timeout.json
```

"Watch what happens. The telemetry router validates every event against our strict Pydantic `TraceEvent` schema — no malformed data ever reaches the analysis layer. Fail Fast by design.

**Action: Switch to the Next.js dashboard**

Now look at the dependency graph. This is **NetworkX** — a directed acyclic graph where every node is a service and every edge is a call hop. The direction matters: it encodes the *caller-to-callee* relationship. You can see the graph has updated in real time:

- `Client` → `API-Gateway` — **green, healthy**
- `API-Gateway` → `Checkout-Service` — **green, healthy**
- `Checkout-Service` → `Payment-Gateway` — **orange, degraded** — 4,800ms latency, SLO is 500ms
- `Payment-Gateway` → `Payment-DB` — **red, FAILED** — connection pool fully exhausted, all 20 connections timed out

This is not a flat log. This is a **directed graph traversal**. The framework immediately identified that `Payment-DB` is the root node of the failure — not Payment-Gateway, not Checkout-Service, even though *those* are the services throwing HTTP 500s. This is the difference between symptom and cause. Graph theory makes it deterministic."

---

## PHASE 3 — THE MAGIC (60 seconds)

**Action: Switch to the `/api/v1/agent/remediate` Swagger UI or run the POST directly**

"Now here is where it gets interesting. The system packages that graph state — all nodes, all edges, all error metadata — and sends it to our AI Decision Engine. But this is not a vanilla ChatGPT call.

**Action: Show the `decision_engine.py` or Swagger response panel**

We use the `google-genai` SDK with `response_schema=RemediationPlan`. This forces Gemini to generate output that **structurally conforms** to our Pydantic model at the token-sampling level — inside the model itself. It is not JSON parsing. It is not regex. It is a type contract enforced before the bytes even leave Google's servers.

Look at what comes back:"

```json
{
  "root_cause": "Payment-DB experienced a DB_TIMEOUT_ERROR with full connection pool exhaustion (20/20 connections, queue depth 87). Upstream propagation caused Payment-Gateway degradation and Checkout-Service HTTP 500, collapsing the entire payment critical path.",
  "impacted_nodes": ["Payment-DB", "Payment-Gateway", "Checkout-Service", "API-Gateway"],
  "suggested_action": "1. Immediately increase Payment-DB connection pool size from 20 to 100. 2. Enable circuit breaker on Payment-Gateway to prevent queue buildup. 3. Deploy read replica for Payment-DB. 4. Drain and restart Payment-Gateway with updated pool config.",
  "target_service": "Payment-DB"
}
```

"Root cause identified. Blast radius mapped. Step-by-step remediation plan generated. In under 3 seconds. No on-call page required.

This is what autonomous infrastructure looks like. Kafka for decoupled event streaming, NetworkX DAGs for precise topology reasoning, and a schema-constrained LLM for deterministic healing — production-grade patterns, running locally on a single machine. Thank you."

---

## POST-DEMO: LIKELY QUESTIONS & ANSWERS

| Question | Sharp Answer |
|---|---|
| *"Why NetworkX over a simple DB query?"* | "Graph traversal is O(V+E). Linear log scanning is O(N²). At 200 services, the graph wins by orders of magnitude." |
| *"Why not just use Datadog?"* | "Datadog detects. This framework diagnoses and heals. It closes the last 90% of the MTTR gap." |
| *"Why Pydantic schema on the LLM?"* | "A malformed LLM response in an autonomous agent does not just break the UI — it can restart the wrong service. Schema enforcement at the LLM boundary converts probabilistic output into a deterministic, typed function call." |
| *"How does this scale?"* | "The modular monolith is the MVP. The architecture doc has the exact extraction path: Kafka producers/consumers, OpenTelemetry, isolated Docker containers — each domain becomes a microservice with zero interface changes." |
