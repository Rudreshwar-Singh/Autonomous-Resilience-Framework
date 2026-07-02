"""
Autonomous Resilience Framework — FastAPI Application Entry Point
==================================================================
This module is the single boot point for the entire backend system.
It initializes the FastAPI application, configures structured logging,
wires up CORS middleware, exposes the /healthz liveness probe, and
registers all domain routers under the /api/v1 namespace.

PHASE 2 SCOPE (Current):
    Four modular domain routers are now registered:
    - /api/v1/incident  → Incident lifecycle management.
    - /api/v1/health    → Detailed dependency-aware health checks.
    - /api/v1/telemetry → Telemetry ingestion and query (REST path;
                          future phases replace POST with Kafka consumer).
    - /api/v1/agent     → AI Remediation Agent triggers and action logs.

    All router endpoints return placeholder payloads in this phase.
    No business logic or domain imports are wired yet — only the
    contract surface (URL schema, HTTP verbs, status codes) is fixed.

ROUTER ISOLATION DESIGN:
    Each domain router lives in its own file (backend/app/routers/<domain>.py)
    and declares its own prefix and tags. main.py's only job is to import
    and mount them. This enforces the bounded-context rule from
    01_architecture.md: no domain logic leaks into the entry point.

DESIGN JUSTIFICATION:
    The lifespan context manager pattern (instead of deprecated @app.on_event)
    provides deterministic startup/shutdown sequencing. This is critical
    because future phases will need to:
    - Phase 2: Initialize Kafka producer connections on startup.
    - Phase 5: Register Prometheus metric collectors.
    - Phase 7: Warm-load LLM client connections.
    By establishing the lifespan pattern now, those integrations drop in
    as additional lines inside the existing async context — no refactoring.

STRUCTURED LOGGING PIPELINE:
    JSON-structured logging is configured at the lifespan level (before any
    request is served) so that every component — including Uvicorn internals
    — outputs machine-parseable log lines. This shields multi-tenant
    telemetry operations from runtime exceptions because:
    1. Log consumers (future Kafka, Loki) never encounter unparseable text.
    2. Consistent schema (timestamp, level, service, message) enables
       automated alerting without per-service regex rules.
    3. Centralized logging setup prevents individual modules from
       accidentally misconfiguring their own loggers.

USAGE:
    uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.logging import setup_logging
from backend.core.settings import get_settings

# ── Domain Router Imports ─────────────────────────────────────────────────────
# Each router is self-contained: it declares its own prefix, tags, and
# endpoints. main.py only mounts them — it never inspects their internals.
# This enforces the bounded-context principle from 01_architecture.md.
from backend.app.routers import agent, health, incident, telemetry

# ── Module-level logger ───────────────────────────────────────────────
# Created here but only usable AFTER setup_logging() is called in lifespan.
logger: logging.Logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# APPLICATION LIFESPAN
# ══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown lifecycle.

    This async context manager runs exactly once:
    - Everything BEFORE 'yield' executes on server startup.
    - Everything AFTER 'yield' executes on server shutdown.

    WHY LIFESPAN OVER @app.on_event:
        FastAPI's @app.on_event("startup") is deprecated as of v0.109.
        The lifespan pattern is the official replacement and provides
        a single, testable function for the entire boot/teardown sequence.

    FUTURE PHASES will add initialization here:
        - Kafka producer connection pool
        - NetworkX graph state initialization
        - LLM client warm-up (Gemini/Groq)
        - Prometheus instrumentation registration
    """
    settings = get_settings()

    # ── STARTUP ───────────────────────────────────────────────────────
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )
    logger.info(
        "Application startup complete — %s v%s",
        settings.APP_NAME,
        settings.APP_VERSION,
    )

    yield  # ← Application serves requests here

    # ── SHUTDOWN ──────────────────────────────────────────────────────
    logger.info("Application shutdown initiated — cleaning up resources")


# ══════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION INSTANCE
# ══════════════════════════════════════════════════════════════════════

settings = get_settings()

app: FastAPI = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A highly concurrent, event-driven self-healing framework that "
        "autonomously detects, diagnoses, and remediates cascading system "
        "failures using NetworkX dependency graph analysis and LLM-powered "
        "remediation agents."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    # Tags organize endpoints in Swagger UI by domain.
    # Future routers will declare their tag when included.
    openapi_tags=[
        {
            "name": "Health",
            "description": "System health and readiness probes.",
        },
        {
            "name": "Incident",
            "description": "Incident lifecycle management and forensic timelines.",
        },
        {
            "name": "Telemetry",
            "description": "Ingest and query simulated telemetry data.",
        },
        {
            "name": "Analysis",
            "description": "Dependency graph state and topology queries.",
        },
        {
            "name": "Agent",
            "description": "AI remediation agent triggers and action logs.",
        },
    ],
)


# ══════════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
# DOMAIN ROUTERS
# ══════════════════════════════════════════════════════════════════════
# Routers are mounted AFTER middleware so that CORS headers are applied
# to every domain endpoint automatically.
#
# WHY SEPARATE FILES:
#   Each router file is the single authoritative source for its domain's
#   URL contract. When a developer searches for telemetry endpoints they
#   open telemetry.py — not a 500-line main.py.
#
# WHY /api/v1/ PREFIX:
#   Versioning at the URL level means the frontend and any external
#   consumers can pin to /api/v1/ while a breaking /api/v2/ is developed
#   in parallel — zero downtime migrations.

app.include_router(incident.router)
app.include_router(health.router)
app.include_router(telemetry.router)
app.include_router(agent.router)


# ══════════════════════════════════════════════════════════════════════
# HEALTH ENDPOINT
# ══════════════════════════════════════════════════════════════════════

@app.get(
    "/healthz",
    tags=["Health"],
    summary="Liveness probe",
    response_description="Returns current application health status.",
)
async def healthz() -> dict[str, Any]:
    """
    Lightweight liveness probe for monitoring and orchestration tools.

    This endpoint is designed to be polled by:
    - Docker HEALTHCHECK directives
    - Prometheus blackbox exporter
    - Frontend dashboard status indicators
    - Load balancers (future production deployments)

    It intentionally performs NO database queries, NO network calls,
    and NO heavy computation — ensuring sub-millisecond response times
    even under high system load.

    Returns:
        dict: A JSON object with status, service name, version, and UTC timestamp.

    Example Response:
        {
            "status": "healthy",
            "service": "Autonomous Resilience Framework",
            "version": "0.1.0",
            "timestamp": "2026-07-02T00:00:00.000Z"
        }
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
