"""
Graph Router
============
Owns all API endpoints in the /api/v1/graph namespace.

DOMAIN RESPONSIBILITY (from 01_architecture.md §2):
    This router is the HTTP boundary for the **Analysis** domain. It exposes
    the NetworkX dependency graph as a REST API, providing the frontend dashboard
    with real-time topology data for visualization.

ENDPOINTS:
    POST /api/v1/graph/analyze
        Accept a batch of TraceEvent logs, run them through GraphAnalyzer,
        and return the full GraphPayload (nodes + edges + meta).

    GET /api/v1/graph/topology
        Return the current in-memory graph snapshot (populated by the last
        /analyze call). Designed for frontend polling.

DESIGN DECISIONS:
    - The GraphAnalyzer is instantiated per-request (stateless). This avoids
      stale state bugs and is safe for the MVP's throughput profile.
    - ``app.state.graph_cache`` stores the last computed GraphPayload so that
      GET /topology can serve the frontend without reprocessing.
    - All request/response bodies are strictly validated Pydantic v2 models.
      This is the "Fail Fast" guardrail from 01_architecture.md §5.

INTEGRATION WITH KAFKA CONSUMER (future phase):
    When the Kafka consumer (backend/telemetry/consumer.py) processes a batch
    of trace events, it will call ``analyze_traces()`` directly (internal
    Python function call — no HTTP, per the Modular Monolith rule) and update
    ``app.state.graph_cache``. The GET /topology endpoint will then serve the
    pre-computed result to the frontend with sub-millisecond latency.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from backend.app.services.graph_analyzer import GraphPayload, analyze_traces
from backend.contracts.events.trace import TraceEvent

# ── Module logger ──────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Router Definition ──────────────────────────────────────────────────────────
router: APIRouter = APIRouter(
    prefix="/api/v1/graph",
    tags=["Analysis"],
)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/analyze",
    response_model=GraphPayload,
    summary="Analyze trace logs and build dependency graph",
    response_description="Full graph payload: nodes, edges, and root-cause metadata.",
    status_code=status.HTTP_200_OK,
)
async def analyze_graph(
    events: list[TraceEvent],
    request: Request,
) -> GraphPayload:
    """
    Accept a batch of distributed trace events, run the GraphAnalyzer, and
    return the complete topology graph as a frontend-ready JSON payload.

    This is the primary entry point for Phase 6. In the MVP, it is called
    directly from the frontend or from mock data scripts. In a future phase,
    the Kafka consumer will call ``analyze_traces()`` as an internal Python
    function call and update ``app.state.graph_cache`` directly.

    Args:
        events:  A list of validated ``TraceEvent`` Pydantic models representing
                 individual inter-service call hops.
        request: FastAPI ``Request`` object used to access ``app.state`` for
                 caching the computed graph payload.

    Returns:
        ``GraphPayload`` — the serialised graph including nodes, edges, and
        root-cause analysis metadata (root_cause_candidate, blast_radius).

    Raises:
        422 Unprocessable Entity: If any event in the payload fails Pydantic validation.
        400 Bad Request: If an empty event list is provided.
        500 Internal Server Error: If an unexpected error occurs in graph construction.
    """
    if not events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event list must not be empty. Provide at least one TraceEvent.",
        )

    logger.info(
        "POST /api/v1/graph/analyze — processing %d trace events", len(events)
    )

    try:
        payload: GraphPayload = analyze_traces(events)
    except (ValueError, RuntimeError) as exc:
        logger.error("GraphAnalyzer failed — error=%s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph analysis failed: {exc}",
        ) from exc

    # Cache the latest computed graph in app.state so the GET /topology
    # endpoint can serve it without reprocessing.
    # WHY app.state: It is the idiomatic FastAPI location for shared, per-process
    # state that is not a database connection (no ORM needed for in-memory cache).
    request.app.state.graph_cache = payload

    logger.info(
        "Graph analysis complete — nodes=%d edges=%d root_cause=%s",
        len(payload.nodes),
        len(payload.edges),
        payload.meta.get("root_cause_candidate"),
    )

    return payload


@router.get(
    "/topology",
    response_model=GraphPayload,
    summary="Retrieve the latest computed topology graph",
    response_description="The most recently computed graph payload, or 404 if not yet available.",
    status_code=status.HTTP_200_OK,
)
async def get_topology(request: Request) -> GraphPayload:
    """
    Return the last graph payload computed by POST /analyze.

    Designed for frontend polling: the dashboard calls this endpoint on a
    short interval (e.g., every 5 seconds) to refresh the topology view
    without re-submitting trace events.

    In a future phase, the Kafka consumer will update ``app.state.graph_cache``
    in the background, and this endpoint will seamlessly serve the live result.

    Args:
        request: FastAPI ``Request`` used to read ``app.state.graph_cache``.

    Returns:
        The cached ``GraphPayload`` from the last successful /analyze call.

    Raises:
        404 Not Found: If no analysis has been run yet in this server session.
    """
    cached: GraphPayload | None = getattr(request.app.state, "graph_cache", None)

    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No graph topology is available yet. "
                "POST to /api/v1/graph/analyze first to build the dependency graph."
            ),
        )

    logger.debug(
        "GET /api/v1/graph/topology — serving cached graph (nodes=%d edges=%d)",
        len(cached.nodes),
        len(cached.edges),
    )

    return cached


@router.get(
    "/health",
    summary="Analysis domain health check",
    response_description="Confirms the Graph Analysis domain is operational.",
    status_code=status.HTTP_200_OK,
)
async def graph_health(request: Request) -> dict[str, Any]:
    """
    Lightweight domain health probe for the Analysis module.

    Returns the current cache status (whether a graph has been computed yet)
    so the frontend dashboard can distinguish between "not yet analyzed"
    and a genuine service failure.

    Returns:
        A JSON object with the domain status and cache availability flag.
    """
    has_cache: bool = getattr(request.app.state, "graph_cache", None) is not None
    return {
        "status": "operational",
        "domain": "analysis",
        "graph_cache_available": has_cache,
    }
