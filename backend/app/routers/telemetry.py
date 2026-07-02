"""
Telemetry Router
================
Owns all API endpoints in the /api/v1/telemetry namespace.

DOMAIN RESPONSIBILITY:
    This router is the primary ingestion boundary for all incoming telemetry
    data — simulated in the MVP, and replaced by an Apache Kafka consumer in
    Phase 2. Its responsibilities include:

    - Accepting raw telemetry payloads from mock data scripts
      (data/fault_scenarios/*.json).
    - Validating each payload against Pydantic contracts in backend/contracts/.
    - Forwarding validated events to the Analysis domain (internal call — no
      HTTP, per the Modular Monolith rule in 01_architecture.md).
    - Exposing a query endpoint so the frontend dashboard can retrieve recent
      telemetry history for rendering sparklines and event feeds.

WHY /api/v1/telemetry SPECIFICALLY:
    When Kafka is introduced in Phase 2, this router continues to exist as the
    REST fallback ingestion path (useful for local testing without a running
    broker). The Kafka consumer will call the same internal validation logic
    that this router calls — no duplication.

CURRENT PHASE (MVP Skeleton):
    All endpoints return a strictly typed placeholder payload to prove the
    routing layer is wired correctly before business logic is implemented.
"""

import logging
from typing import Any

from fastapi import APIRouter

# ── Module logger ─────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Router Definition ─────────────────────────────────────────────────────────
router: APIRouter = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["Telemetry"],
)

# ── Placeholder Payload ───────────────────────────────────────────────────────
_PLACEHOLDER: dict[str, str] = {"status": "placeholder", "service": "telemetry"}


@router.get(
    "/",
    summary="Retrieve recent telemetry events",
    response_description="Placeholder response — no business logic yet.",
)
async def list_telemetry_events() -> dict[str, Any]:
    """
    Return a chronological list of recently ingested telemetry events.

    FUTURE IMPLEMENTATION:
        Query an in-memory deque (or future time-series store) for the last N
        validated TelemetryEvent Pydantic models. Supports optional query
        params: ?limit=50&service=payment-svc&level=ERROR

    Returns:
        dict: Placeholder JSON payload confirming the router is reachable.
    """
    logger.debug("GET /api/v1/telemetry/ called — returning placeholder")
    return _PLACEHOLDER


@router.post(
    "/ingest",
    summary="Ingest a single telemetry event",
    status_code=202,
    response_description="Placeholder response — no business logic yet.",
)
async def ingest_telemetry_event() -> dict[str, Any]:
    """
    Accept a single telemetry event from a mock data script or future
    OpenTelemetry agent.

    FUTURE IMPLEMENTATION:
        Deserialise the request body into a TelemetryEventRequest Pydantic
        model (defined in backend/contracts/). Validate all fields strictly,
        log the event as a structured JSON record, and dispatch the validated
        model to the Analysis domain via an internal function call.

    Returns:
        dict: Placeholder JSON payload confirming the router is reachable.
    """
    logger.debug("POST /api/v1/telemetry/ingest called — returning placeholder")
    return _PLACEHOLDER
