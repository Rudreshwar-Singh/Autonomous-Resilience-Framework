"""
Telemetry Router
================
Owns all API endpoints in the /api/v1/telemetry namespace.

DOMAIN RESPONSIBILITY:
    This router is the primary REST ingestion boundary for all incoming telemetry
    data. Its responsibilities include:

    - Accepting raw telemetry payloads validated against the TelemetryEvent
      Pydantic contract (backend/contracts/events/telemetry.py).
    - Serialising valid events to Kafka via the KafkaProducerService so that
      downstream consumers (consumer.py, Analysis domain) process them
      asynchronously without blocking the HTTP response cycle.
    - Returning HTTP 202 Accepted immediately — the event is enqueued, not yet
      processed, which is the semantically correct response for async pipelines.
    - Exposing a query endpoint so the frontend dashboard can retrieve recent
      telemetry history for sparklines and event feeds (future phase).

WHY THE ROUTER DOES NOT OWN THE PRODUCER:
    The router's only job is to translate HTTP concerns (request body, status
    code, response schema) into domain operations.  Kafka connection logic is
    infrastructure — it belongs in services/.  See 01_architecture.md §
    "Separation of Concerns" and the architectural justification at the bottom
    of this file's module docstring.

WHY /api/v1/telemetry SPECIFICALLY:
    When Kafka is introduced, this router continues to exist as the REST
    fallback ingestion path (useful for local testing without a running broker).
    The Kafka consumer calls the same internal validation logic — no duplication.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request, Response

from backend.contracts.events.telemetry import TelemetryEvent
from backend.core.settings import get_settings

# ── Module logger ─────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Cached settings ───────────────────────────────────────────────────────────
_settings = get_settings()

# ── Router Definition ─────────────────────────────────────────────────────────
router: APIRouter = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["Telemetry"],
)


# ══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════


@router.get(
    "/",
    summary="Retrieve recent telemetry events",
    response_description="Placeholder response — query store not yet implemented.",
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
    return {"status": "placeholder", "service": "telemetry"}


@router.post(
    "/ingest",
    summary="Ingest a single telemetry event",
    status_code=202,
    response_description=(
        "202 Accepted — event has been enqueued to Kafka; "
        "not yet processed by the consumer."
    ),
)
async def ingest_telemetry_event(
    event: TelemetryEvent,
    request: Request,
) -> dict[str, Any]:
    """
    Accept a single validated telemetry event and publish it to Kafka.

    The endpoint returns **202 Accepted** rather than 200 OK because the
    caller's event is enqueued (not yet consumed or processed).  This is the
    correct HTTP semantic for async pipelines — see RFC 7231 §6.3.3.

    The KafkaProducerService is retrieved from ``request.app.state`` — set
    during the lifespan startup in ``main.py``.  This avoids global state and
    keeps the router testable: tests can inject a mock producer via
    ``app.state.kafka_producer`` without patching module-level variables.

    Args:
        event:   Validated ``TelemetryEvent`` Pydantic model, deserialised
                 from the JSON request body.
        request: FastAPI Request object, used to access ``app.state``.

    Returns:
        dict: JSON body confirming acceptance with the event_id echoed back
              so the caller can correlate the event in future audit queries.

    Raises:
        HTTP 422 Unprocessable Entity: If the request body fails Pydantic
            validation (wrong types, missing required fields, enum mismatch).
        HTTP 500 Internal Server Error: If the Kafka broker is unreachable
            and the producer's internal buffer is full (BufferError).
    """
    # Retrieve the shared producer from app.state — instantiated in lifespan.
    kafka_producer = request.app.state.kafka_producer

    kafka_producer.produce(
        topic=_settings.KAFKA_TOPIC_TELEMETRY,
        event=event,
    )

    logger.info(
        "Telemetry event accepted — event_id=%s service=%s level=%s",
        event.event_id,
        event.service_name,
        event.level.value,
    )

    return {
        "status": "accepted",
        "event_id": str(event.event_id),
        "topic": _settings.KAFKA_TOPIC_TELEMETRY,
        "message": "Event enqueued for asynchronous processing.",
    }
