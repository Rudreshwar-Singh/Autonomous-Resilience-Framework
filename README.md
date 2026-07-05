<div align="center">

# 🛡️ Autonomous Resilience Framework

### `[WIP — Active Development]`

**A self-healing distributed systems engine that autonomously detects, diagnoses, and remediates cascading infrastructure failures using real-time telemetry analysis, dynamic dependency graph mapping, and LLM-powered remediation agents.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-Streaming-231F20?logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![NetworkX](https://img.shields.io/badge/NetworkX-Graph%20Analysis-4B8BBE)](https://networkx.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Development Roadmap](#-development-roadmap)
- [Future Evolution](#-future-evolution)
- [Contributing](#-contributing)

---

## 🎯 Problem Statement

Modern distributed systems suffer from **cascading failures** — a single degraded service triggers a chain reaction across dependent components, often faster than human operators can diagnose and respond.

The Autonomous Resilience Framework addresses this by:

1. **Real-Time Telemetry Ingestion** — Capturing simulated system logs, metrics, and traces from microservice endpoints.
2. **Dynamic Dependency Graph Analysis** — Building a live, directed graph (NetworkX) of service-to-service communication patterns to identify failure propagation paths.
3. **LLM-Powered Autonomous Remediation** — Feeding the failure graph state and error traces into an AI agent that outputs deterministic, validated remediation strategies.

> **Interview Context:** This project demonstrates production-grade engineering patterns — event-driven architecture, strict data contracts (Pydantic v2), structured observability, and modular domain boundaries — while remaining fully runnable on a local Windows 11 development machine.

---

## 🏗️ System Architecture

The system follows an **evolutionary architecture** pattern: starting as a Modular Monolith (MVP) with strict domain boundaries, designed for a seamless transition to event-driven microservices.

### MVP Phase — Modular Monolith

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                         │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │  Telemetry   │──▶│   Analysis   │──▶│    AI Agent           │    │
│  │  (Ingestion) │   │  (NetworkX)  │   │  (Deterministic /    │    │
│  │              │   │              │   │   LLM Remediation)   │    │
│  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘    │
│         │                  │                      │                │
│         └──────────────────┴──────────────────────┘                │
│                    Pydantic v2 Data Contracts                      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Next.js Frontend │
                    │   (Dashboard UI)   │
                    └───────────────────┘
```

### End-to-End Data Flow

```
Fault Injection → Telemetry Ingestion → Pydantic Validation → NetworkX Graph Update
    → Failure Threshold Breach → AI Agent Diagnosis → Validated Remediation Action
    → Execution & Logging → Frontend Dashboard Visualization
```

### Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Strict Boundaries** | Domains communicate only via validated Pydantic models — no shared state |
| **Fail Fast** | All external inputs validated at the boundary before processing |
| **No Circular Dependencies** | Shared components live in `contracts/` and `core/` |
| **Explainability** | All complex logic (graph traversals, LLM prompts) is heavily documented |

---

## 🔧 Technology Stack

### Backend & Infrastructure

| Technology | Purpose | Phase |
|-----------|---------|-------|
| **Python 3.12** | Core language — strict typing, modern syntax | All |
| **FastAPI** | Async web framework — auto-generated OpenAPI docs | 1+ |
| **Pydantic v2** | Data validation & serialization at all boundaries | All |
| **Apache Kafka** | Real-time telemetry event streaming | 5 |
| **NetworkX** | Directed dependency graph construction & traversal | 6 |
| **Prometheus** | Metrics collection and storage | 2+ |
| **Grafana** | Metrics visualization dashboards | 2+ |
| **Docker Compose** | Local multi-container orchestration | 2 |

### Frontend

| Technology | Purpose | Phase |
|-----------|---------|-------|
| **Next.js (React)** | Dashboard UI framework | 4 |
| **Tailwind CSS** | Utility-first styling | 4 |
| **shadcn/ui** | Pre-built accessible UI components | 4 |

### AI & Remediation

| Technology | Purpose | Phase |
|-----------|---------|-------|
| **Google Gemini (Free Tier)** | LLM for root cause analysis & remediation | 7 |
| **Groq (Free Tier)** | Alternative fast inference LLM | 7 |
| **Ollama** | Local LLM fallback for offline development | 7 |

### Testing & Quality

| Technology | Purpose | Phase |
|-----------|---------|-------|
| **Pytest** | Unit & integration testing framework | 8 |
| **Structured JSON Logging** | Machine-parseable observability output | 1+ |

---

## 📁 Project Structure

```
Autonomous-Resilience-Framework/
│
├── backend/                    # Core application (Modular Monolith)
│   ├── app/                    # FastAPI application entry point
│   │   ├── main.py             # Application factory, lifespan, /healthz
│   │   ├── routers/            # API endpoint routers (per domain)
│   │   │   ├── telemetry.py    # POST /api/v1/telemetry — log ingestion
│   │   │   ├── graph.py        # POST /api/v1/graph/analyze — topology engine  [Phase 6]
│   │   │   ├── incident.py     # /api/v1/incident — incident lifecycle
│   │   │   ├── health.py       # /api/v1/health — dependency health checks
│   │   │   └── agent.py        # /api/v1/agent — AI remediation triggers
│   │   └── dependencies.py     # FastAPI dependency injection
│   ├── services/               # Business logic layer
│   │   ├── kafka_producer.py   # Lifecycle-managed Kafka producer service
│   │   └── graph_analyzer.py   # NetworkX DiGraph builder + GraphPayload export  [Phase 6]
│   ├── core/                   # Shared infrastructure
│   │   ├── settings.py         # Pydantic BaseSettings configuration
│   │   ├── logging.py          # Structured JSON logging setup
│   │   ├── config.py           # Additional config utilities
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   └── security.py         # Auth utilities (future phases)
│   ├── contracts/              # Cross-domain data contracts (single source of truth)
│   │   ├── api/                # Request/response Pydantic models
│   │   └── events/
│   │       ├── telemetry.py    # TelemetryEvent — flat service log schema
│   │       └── trace.py        # TraceEvent + ErrorMetadata — hop-level schema  [Phase 6]
│   ├── models/                 # Domain models
│   ├── schemas/                # Data schemas
│   ├── middleware/             # Custom middleware
│   ├── utils/                  # Shared utilities
│   ├── telemetry/              # Kafka consumer worker (standalone process)
│   │   └── consumer.py         # Polls system-telemetry topic, validates TelemetryEvent
│   ├── logs/                   # File-based log storage
│   └── requirements.txt        # Python dependencies
│
├── telemetry/                  # Telemetry domain (future phase)
├── analysis/                   # Graph analysis domain (future phase)
├── microservices/              # Extracted microservices (future phase)
│
├── frontend/                   # Next.js dashboard (Phase 4)
│
├── data/                       # Test data & scenarios
│   ├── demo/                   # Demo datasets
│   ├── fault_scenarios/        # Synthetic fault injection configs
│   ├── sample_logs/            # Sample telemetry logs
│   └── sample_metrics/         # Sample metric data
│
├── infra/                      # Infrastructure configs
│   ├── docker/                 # Docker Compose files
│   └── monitoring/             # Prometheus/Grafana configs
│
├── tests/                      # Test suite (Phase 8)
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── load/                   # Load/performance tests
│
├── scripts/                    # Developer automation scripts
├── docs/                       # Extended documentation
├── presentation/               # Demo slides & scripts
│
├── PROJECT_BIBLE/              # Design docs & constraints
│   ├── 00_project_charter.md   # Project vision & goals
│   ├── 01_architecture.md      # Architecture strategy document
│   ├── 97_definition_of_done.md# Quality gates checklist
│   └── 98_project_constraints.md# Technology & design constraints
│
├── .github/workflows/          # CI/CD pipelines (future)
├── .gitignore                  # Version control exclusions
└── README.md                   # ← You are here
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** — [Download](https://python.org/downloads/)
- **Docker Desktop** — [Download](https://docker.com/products/docker-desktop/) (for Phase 2+)
- **Node.js 18+** — [Download](https://nodejs.org/) (for Phase 4+)
- **Windows 11** — Primary development platform

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Rudreshwar-Singh/Autonomous-Resilience-Framework.git
cd Autonomous-Resilience-Framework

# 2. Create and activate Python virtual environment
python -m venv backend/.venv
backend\.venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Start the development server
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Verify Installation

| Endpoint | Method | Expected Result |
|----------|--------|-----------------|
| [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz) | `GET` | `{"status": "healthy", ...}` |
| [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | `GET` | Interactive Swagger UI |
| [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | `GET` | ReDoc API documentation |
| [http://127.0.0.1:8000/api/v1/graph/health](http://127.0.0.1:8000/api/v1/graph/health) | `GET` | `{"status": "operational", "domain": "analysis", ...}` |

### Phase 6 — Run the Graph Topology Engine

```bash
# Run the test harness directly (no server needed)
python -m backend.app.services.graph_analyzer
```

Expected output — a clean JSON graph payload with cascading failure detected:
```json
{
  "nodes": [
    { "id": "Client",       "status": "success" },
    { "id": "API-Gateway",  "status": "success" },
    { "id": "Auth-Service", "status": "failed",   "error_metadata": { "error_code": "500_INTERNAL_SERVER_ERROR" } },
    { "id": "User-DB",      "status": "failed",   "error_metadata": { "error_code": "DB_TIMEOUT_ERROR" } },
    { "id": "Notification-Service", "status": "degraded" }
  ],
  "edges": [
    { "source": "Client",       "target": "API-Gateway",  "weight": 1 },
    { "source": "API-Gateway",  "target": "Auth-Service", "weight": 2 },
    { "source": "Auth-Service", "target": "User-DB",      "weight": 1 }
  ],
  "meta": {
    "root_cause_candidate": "Auth-Service",
    "blast_radius": ["Client", "API-Gateway"]
  }
}
```

### Phase 6 — Test the Analysis REST API

```bash
# Start the server
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# POST trace events to build the dependency graph
curl -X POST http://127.0.0.1:8000/api/v1/graph/analyze \
  -H "Content-Type: application/json" \
  -d '[
    {"trace_id": "req-001", "timestamp": "2026-07-05T12:00:01Z", "source_node": "Client", "target_node": "API-Gateway", "status": "success"},
    {"trace_id": "req-001", "timestamp": "2026-07-05T12:00:02Z", "source_node": "API-Gateway", "target_node": "Auth-Service", "status": "failed",
     "error_metadata": {"error_code": "500_INTERNAL_SERVER_ERROR", "message": "Auth dependency failed"}}
  ]'

# Poll the cached topology (for frontend dashboard)
curl http://127.0.0.1:8000/api/v1/graph/topology
```

---

## 📈 Development Roadmap

| Phase | Milestone | Status |
|-------|-----------|--------|
| **0** | Project Foundation — Directory structure, PROJECT_BIBLE, constraints | ✅ Complete |
| **1** | Backend Foundation — FastAPI shell, `/healthz`, structured logging, Swagger | ✅ Complete |
| **2** | Docker Infrastructure — Kafka, Zookeeper, Prometheus, Grafana containers | ✅ Complete |
| **3** | Windows Scripts — PowerShell automation (`dev.ps1`) | ✅ Complete |
| **4** | Frontend Dashboard — Next.js + shadcn/ui observability UI | ✅ Complete |
| **5** | Telemetry Pipeline — Kafka producer/consumer for log streaming | ✅ Complete |
| **6** | NetworkX Brain — Dependency graph construction from telemetry data | ✅ Complete |
| **7** | AI Agent — LLM-powered diagnosis & deterministic remediation engine | ⬚ Planned |
| **8** | Testing Suite — Pytest unit, integration, and load tests | ⬚ Planned |
| **9** | Presentation — Demo deck, live walkthrough script, fault scenarios | ⬚ Planned |

---

## 🔮 Future Evolution

The system is intentionally designed with an **evolutionary architecture** that supports incremental migration without major refactoring.

### Current: Deterministic Python Agent (MVP)

The MVP remediation agent is a deterministic, strictly-typed Python module that:
- Receives failure graph state and error traces as Pydantic models
- Calls a free-tier LLM (Gemini/Groq) with a structured prompt
- Validates the LLM response against a strict Pydantic schema
- Executes validated remediation actions locally

### Future: LangGraph Orchestration Layer (Post-MVP)

The architecture is designed so the deterministic agent can be **replaced or wrapped** by a LangGraph-based multi-agent orchestration layer without changing the surrounding services:

```
┌─────────────────────────────────────────────────────┐
│                Current (MVP)                         │
│  Telemetry → Analysis → [Deterministic Agent] → UI  │
└─────────────────────────────────────────────────────┘
                        ↓ (drop-in replacement)
┌─────────────────────────────────────────────────────┐
│                Future (Post-MVP)                     │
│  Telemetry → Analysis → [LangGraph Orchestrator]    │
│                          ├─ Diagnosis Agent          │
│                          ├─ Remediation Agent        │
│                          └─ Verification Agent → UI  │
└─────────────────────────────────────────────────────┘
```

### Additional Future Phases

- **Event-Driven Microservices** — Internal function calls replaced by Kafka producers/consumers
- **OpenTelemetry Integration** — Standardized tracing replacing manual mock injection
- **Containerized Domain Extraction** — Each domain split into its own Docker container
- **Flutter Mobile Dashboard** — Cross-platform mobile monitoring interface

---

## 🤝 Contributing

This project is under active development. Contributions, suggestions, and feedback are welcome.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with** ❤️ **for learning, interviews, and real-world distributed systems engineering.**

</div>
