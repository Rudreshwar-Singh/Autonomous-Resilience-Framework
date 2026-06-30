# Project Constraints

These constraints define the technologies, architecture, and development boundaries for the Autonomous Resilience Framework. All development should follow these constraints unless they are intentionally updated in a future milestone.

## Technology Stack (Backend & Infra)
- Python 3.12
- FastAPI
- Docker & Docker Compose
- Apache Kafka (Telemetry streaming)
- Prometheus & Grafana (Metrics & Visualization)
- NetworkX (Topology mapping)

## Technology Stack (Frontend)
- Next.js (React)
- Tailwind CSS & shadcn/ui
- *Future:* Flutter compatibility for mobile expansion

## Architecture Constraints
- REST APIs first (Internal function calls for MVP, REST/Kafka for Microservices).
- Everything MUST be capable of running locally.
- Windows 11 compatibility is strictly required for local development.
- No database (PostgreSQL/MongoDB) unless absolutely required; rely on in-memory or simple file storage for the MVP.
- No authentication or RBAC in the MVP phase.

## AI & Development Constraints
- **No Paid APIs:** The AI Remediation Agent must utilize free-tier LLM APIs (e.g., Google Gemini Free Tier, Groq) or local models (Ollama). Do not implement paid OpenAI/Anthropic calls.
- **No Kubernetes:** Do not introduce K8s before Milestone 2 (Docker Compose is the standard for MVP).
- **No LangGraph/CrewAI:** Implement a deterministic, strictly-typed Pydantic-based Python agent first before introducing complex multi-agent frameworks.

## Code Quality & Engineering Standards
- **Strict Typing:** All Python code must use Python 3.12 type hints.
- **Data Validation:** All boundaries and LLM outputs must be strictly validated using Pydantic v2.
- **Interview Quality:** Code must be modular, heavily commented, and self-documenting. Prioritize readability over clever one-liners.

## Goal
Maintain a simple, interview-quality, modular project that is easy to understand, demonstrate, and extend in future milestones.