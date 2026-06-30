# Architectural Strategy: Autonomous Resilience Framework

This document outlines the architectural progression of the Autonomous Resilience Framework. We employ an evolutionary architecture approach: starting with a highly cohesive, easily testable Modular Monolith, and establishing strict boundaries that allow for a seamless transition to a Distributed Event-Driven Microservices architecture.

## 1. Current Phase: Modular Monolith (MVP)
To ensure rapid development, tight feedback loops, and reliable local testing (optimized for Windows 11), the system is initially built as a **Modular Monolith**. 
- **Single Process:** All backend domains (Telemetry, Analysis, AI Remediation) run within a single FastAPI application instance.
- **In-Memory Communication:** Domains communicate via internal Python function calls and shared interfaces, NOT via network requests.
- **Strict Boundaries:** To prepare for the future microservices split, domains are strictly decoupled. They may only communicate by passing validated Pydantic models (data contracts). Direct database or state sharing across domains is prohibited.

## 2. Directory Structure Rules (Domain-Driven Design)
The `backend/` directory is logically separated by domain to enforce bounded contexts. Every domain acts as an independent module:

- `backend/telemetry/`: Responsible for receiving, validating, and standardizing incoming simulated logs and metrics.
- `backend/analysis/`: Maintains the system state. Uses NetworkX to build dynamic, directed graphs of the system topology to identify bottlenecks and cascaded failures.
- `backend/agent/`: The brain of the system. Ingests failure traces and graph states, interfaces with LLM APIs, and outputs deterministic remediation strategies.
- `backend/contracts/`: The single source of truth for all cross-domain communication. Contains standard JSON event schemas and Pydantic validation models.
- `backend/core/`: Shared configurations (`settings.py`), logging setups, middleware, and security utilities.
- `backend/logs/`: Local file-based logging storage for auditability and debugging.

## 3. End-to-End Data Flow (MVP Phase)
1. **Simulation (Injection):** Mock data scripts from `data/fault_scenarios/` inject synthetic system faults (e.g., `payment_timeout.json`) into the system.
2. **Ingestion (Telemetry):** FastAPI endpoints receive the telemetry data, validate it against Pydantic schemas in `contracts/`, and log the event.
3. **Topology Mapping (Analysis):** The telemetry event is passed to the Analysis domain, which updates the NetworkX dependency graph to reflect degraded node health.
4. **Diagnosis (Agent):** If a failure threshold is breached, the Agent domain is triggered. It packages the current NetworkX graph state and the error traceback into a structured prompt for the LLM.
5. **Mitigation (Action):** The LLM returns a strictly validated JSON payload dictating the root cause and the required mitigation (e.g., "Restart Payment Service"). A local deterministic function executes and logs this "healing" action.
6. **Visualization (UI):** The Next.js frontend constantly polls (or listens via WebSockets) to the FastAPI backend to render the live network graph and incident logs.

## 4. Future Phase: Event-Driven Microservices (Do NOT implement yet)
Once the local deterministic agent works flawlessly and the core logic is validated, the application will be extracted into a distributed architecture. 
*Note: Do not write code for this phase until explicitly instructed.*

**The Evolution Path:**
- **Kafka Integration:** Internal Python function calls between `telemetry`, `analysis`, and `agent` will be replaced by Apache Kafka Producers and Consumers.
- **OpenTelemetry:** Standardized OpenTelemetry agents will replace the manual mock data injection, wrapping around actual running services.
- **Prometheus:** The in-memory metric aggregation will be exported to a dedicated Prometheus container.
- **Containerization:** The logical domains will be split into isolated Docker containers defined in `infra/docker/docker-compose.yml`.

## 5. Architectural Guardrails
- **No Circular Dependencies:** Domains must never import from each other in a circular loop. If a shared component is needed, it belongs in `backend/contracts/` or `backend/core/`.
- **Fail Fast:** All external inputs (UI, simulated data, future APIs) must be strictly validated at the boundary using Pydantic. 
- **Explainability:** Because this is an interview/portfolio project, all complex logic (especially NetworkX graph traversals and LLM prompt engineering) must be heavily commented and easy to whiteboard.
