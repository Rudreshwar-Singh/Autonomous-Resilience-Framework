# Project Charter: Autonomous Resilience Framework

## 1. Project Identity & Vision
- **Name:** Autonomous Resilience Framework (Antigravity IDE)
- **Project Type:** AI-powered Distributed Systems & Autonomous Infrastructure Platform
- **Purpose:** Portfolio flagship project, interview showcase, hackathon submission, and foundation for future product development.
- **Primary Vision:** Build an enterprise-grade portfolio project demonstrating mastery of distributed systems, AI integration, and reliability engineering.
- **Secondary Vision:** Establish an architecture that can evolve into a production-grade platform or startup in the future.
- **Immediate Use Cases:** Resume enhancement, highly technical placement interviews (e.g., Google, Salesforce), and competitive hackathons (e.g., Flipkart GRID).
- **Core Objective:** Build a scalable, production-ready system capable of monitoring, detecting, and autonomously healing network/service failures using AI agents and graph-based topology.

## 2. The Core Problem (Problem Statement)
Modern distributed systems suffer from cascading failures. Traditional monitoring platforms detect failures but still rely heavily on manual intervention. The Autonomous Resilience Framework aims to close this gap by continuously monitoring infrastructure, identifying root causes using graph-based analysis, and autonomously executing recovery strategies through intelligent agents while providing full observability and explainability.

## 3. Project Scope
**In-Scope (MVP):**
- A modular FastAPI backend simulating a distributed service environment.
- Real-time telemetry ingestion using OpenTelemetry and Apache Kafka.
- Metric aggregation using Prometheus.
- Live system topology mapping using NetworkX.
- A deterministic AI Remediation Agent that parses error traces and graph data to recommend and execute fixes via strictly typed LLM outputs.
- A frontend dashboard for observing system health, graph dependencies, and AI agent logs.

**Out-of-Scope (MVP Phase):**
- Complex Kubernetes (K8s) multi-cluster orchestration (to be simulated via Docker Compose for local development).
- User Authentication, Role-Based Access Control (RBAC), and Billing.
- Training custom LLMs (will use established API models like OpenAI/Anthropic/Bedrock).

## 4. Technologies
- **Backend Framework:** FastAPI (Python 3.12)
- **Data Ingestion & Streaming:** OpenTelemetry, Apache Kafka
- **Observability & Metrics:** Prometheus
- **Graph Analytics:** NetworkX
- **AI & Logic:** LLM APIs (OpenAI/Anthropic), Pydantic (for deterministic schema validation)
- **Frontend / UI:** Next.js (React), Tailwind CSS, shadcn/ui
- **Infrastructure & Deployment:** Docker, Docker Compose, GitHub Actions (CI/CD)

## 5. Success Criteria
1. **Technical Viability:** The system successfully detects a simulated fault, routes telemetry through Kafka, updates the NetworkX topology graph, and triggers the AI Agent.
2. **Deterministic Healing:** The AI Agent consistently outputs a valid, parseable JSON schema containing the correct root cause and a valid mitigation action (e.g., "Restart Router").
3. **Professional Quality:** The codebase passes all linting rules, has comprehensive unit/integration tests, and contains robust documentation.
4. **Career Impact:** The project serves as a compelling talking point in Staff-level or high-tier intern interviews (e.g., Google, Salesforce), easily demonstrable via a local execution script.

## 6. Deliverables
- Fully functional GitHub Repository with clean commit history and branch management.
- `docker-compose.yml` for 1-click local environment spin-up.
- `PROJECT_BIBLE` directory containing comprehensive architectural and design decisions (ADRs).
- Interactive Frontend Dashboard demonstrating live system topology and logs.
- Dedicated `demo/` folder containing data generation scripts for repeatable presentation scenarios (e.g., `payment_timeout.json`).

## 7. Timeline & Milestones
- **Week 1 (Monolith & UI):** Setup project structure, build FastAPI modular monolith, establish standard contracts, and initialize Next.js dashboard.
- **Week 2 (Streaming & Metrics):** Integrate OpenTelemetry, deploy Kafka via Docker, and configure Telemetry Consumer.
- **Week 3 (Graph & Topology):** Setup Prometheus scraping and build the NetworkX dynamic dependency graph.
- **Week 4 (AI Agent & Polish):** Implement deterministic AI remediation logic, write unit/integration tests, prepare presentation assets, and finalize the README.

## 8. AI Assistant Persona & Role
- You are acting as a Senior Staff Engineer and Technical Mentor.
- Your goal is to help me build an interview-quality, modular, and well-documented software system.
- Prioritize clean architecture, maintainability, readability, and local testability over unnecessary enterprise complexity during the MVP phase.
- Every implementation should be easy to explain during technical interviews.
- Before suggesting new libraries, frameworks, or architectural changes, always verify they comply with `98_project_constraints.md` (or equivalent guidelines).
- Explain significant design decisions and trade-offs whenever introducing new components.

**Design Principle:** Build a simple, modular MVP first, then iteratively evolve it into a scalable platform through clearly defined milestones.

