"""
Agent Router
============
Owns all API endpoints in the /api/v1/agent namespace.

DOMAIN RESPONSIBILITY:
    This router is the HTTP control plane for the AI Remediation Agent —
    the "brain" of the Autonomous Resilience Framework. Its responsibilities:

    - Expose a ``POST /api/v1/agent/remediate`` endpoint so the frontend
      dashboard (or an internal Analysis domain trigger) can dispatch a
      graph payload and receive a validated RemediationPlan in response.
    - Expose a ``GET /api/v1/agent/actions`` endpoint so the frontend can
      render the chronological log of past agent decisions (skeleton only —
      full implementation deferred to a future milestone).

    PHASE 7 IMPLEMENTATION:
    The ``/remediate`` endpoint now calls the real ``DecisionEngine`` service,
    which sends the graph payload to Google Gemini (free-tier) and returns
    a strictly validated ``RemediationPlan`` Pydantic model.

    The router does NOT:
    - Contain LLM or business logic (that lives in ``decision_engine.py``).
    - Manage graph state (that lives in ``graph_analyzer.py``).
    - Make direct calls between domains other than through the
      ``contracts/api/`` Pydantic layer (01_architecture.md §1).

HOW THE DecisionEngine IS INJECTED:
    We use FastAPI's dependency injection (``Depends``) pattern with
    ``app.state`` to retrieve the shared ``DecisionEngine`` instance
    initialised in the lifespan context.  This avoids creating a new
    Gemini HTTP client per request.

NOTE: Per 98_project_constraints.md, no paid LLM APIs (OpenAI/Anthropic) shall
    be used. Only Gemini Free Tier, Groq, or local Ollama models.

REFERENCES:
    - 01_architecture.md §3 (Agent domain: Diagnosis + Mitigation steps)
    - 98_project_constraints.md (No paid APIs, Pydantic v2)
    - 99_ai_rules.md (Strict typing, structured logging, FastAPI DI)
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from backend.contracts.api.agent import RemediateRequest, RemediationPlan
from backend.app.services.decision_engine import DecisionEngine

# ── Module logger ─────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Router Definition ─────────────────────────────────────────────────────────
router: APIRouter = APIRouter(
    prefix="/api/v1/agent",
    tags=["Agent"],
)


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY INJECTION — DecisionEngine from app.state
# ══════════════════════════════════════════════════════════════════════════════


def get_decision_engine(request: Request) -> DecisionEngine:
    """
    FastAPI dependency that retrieves the shared ``DecisionEngine`` instance
    from ``app.state``.

    WHY ``app.state`` INSTEAD OF DIRECT INSTANTIATION?
        Creating a ``genai.Client`` opens an HTTP connection pool and reads
        environment variables.  Doing this inside every request handler
        would add latency and waste resources.  The ``app.state`` pattern
        (established in main.py's lifespan context) ensures the client is
        created exactly once at startup and reused across all requests —
        the same approach used by ``KafkaProducerService``.

    USAGE IN ROUTE HANDLER:
        engine: DecisionEngine = Depends(get_decision_engine)

    Raises:
        HTTPException 503: If the engine was not initialised at startup
                           (e.g., missing GEMINI_API_KEY).
    """
    engine: DecisionEngine | None = getattr(request.app.state, "decision_engine", None)
    if engine is None:
        logger.error(
            "DecisionEngine not found in app.state — "
            "GEMINI_API_KEY may be missing or lifespan init failed."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI Decision Engine is not available.  "
                "Ensure GEMINI_API_KEY is set and the server was restarted."
            ),
        )
    return engine


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/remediate",
    response_model=RemediationPlan,
    status_code=status.HTTP_200_OK,
    summary="Analyse a fault graph and generate an AI remediation plan",
    response_description=(
        "A Pydantic-validated RemediationPlan containing the root cause, "
        "blast radius (impacted nodes), target service, and a step-by-step "
        "remediation action produced by Google Gemini."
    ),
)
async def remediate(
    body: RemediateRequest,
    engine: DecisionEngine = Depends(get_decision_engine),
) -> RemediationPlan:
    """
    Accept a NetworkX graph payload from Phase 6 and return an AI-generated,
    schema-validated remediation plan.

    FLOW:
        1. FastAPI validates the request body against ``RemediateRequest``
           (Fail Fast at the HTTP boundary — 01_architecture.md §5).
        2. The ``DecisionEngine`` builds a structured prompt from the graph
           payload and optional error traceback.
        3. Gemini generates a response constrained to the ``RemediationPlan``
           JSON schema (structured output mode).
        4. Pydantic validates the LLM response a second time.
        5. FastAPI serialises the ``RemediationPlan`` to JSON via
           ``response_model=RemediationPlan``.

    Args:
        body:   The validated request body containing ``graph_payload``
                (Phase 6 GraphPayload dict) and an optional
                ``error_traceback`` string.
        engine: The shared ``DecisionEngine`` instance from ``app.state``
                (injected by ``get_decision_engine`` dependency).

    Returns:
        ``RemediationPlan`` — root_cause, impacted_nodes,
        suggested_action, target_service.

    Raises:
        422 Unprocessable Entity: If the request body fails Pydantic validation.
        503 Service Unavailable:  If the DecisionEngine is not initialised.
        502 Bad Gateway:          If the Gemini API returns a non-2xx error.
    """
    logger.info(
        "POST /api/v1/agent/remediate — nodes=%d edges=%d traceback_provided=%s",
        len(body.graph_payload.get("nodes", [])),
        len(body.graph_payload.get("edges", [])),
        body.error_traceback is not None,
    )

    try:
        plan: RemediationPlan = engine.analyze_fault_graph(
            graph_payload=body.graph_payload,
            error_traceback=body.error_traceback,
        )
    except ValueError as exc:
        # Malformed graph_payload (missing keys, etc.)
        logger.warning("Invalid graph_payload received — %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid graph_payload: {exc}",
        ) from exc
    except ValidationError as exc:
        # LLM returned something that failed Pydantic field constraints.
        logger.error("RemediationPlan validation failed — %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI model returned an invalid response that did not "
                "satisfy the RemediationPlan schema.  Please retry."
            ),
        ) from exc
    except Exception as exc:
        # Catch-all for Gemini APIError, network timeouts, etc.
        # We deliberately don't expose the raw SDK error to the client.
        logger.error(
            "DecisionEngine raised an unexpected error — %s: %s",
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"AI Decision Engine error: {type(exc).__name__}.  "
                "Check server logs for details."
            ),
        ) from exc

    logger.info(
        "RemediationPlan returned — target_service=%r impacted_count=%d",
        plan.target_service,
        len(plan.impacted_nodes),
    )
    return plan


@router.get(
    "/actions",
    summary="List past agent remediation actions",
    response_description=(
        "Chronological log of all remediation actions executed by the AI Agent "
        "(skeleton — full implementation in a future milestone)."
    ),
)
async def list_agent_actions() -> dict[str, Any]:
    """
    Return the chronological log of all remediation actions executed by the
    AI Agent.

    FUTURE IMPLEMENTATION:
        Query the agent action log (in-memory list or file-based store in
        backend/logs/) and return a list of RemediationPlan Pydantic models.
        Each record will include: trace_id, root_cause, action_taken,
        llm_model_used, execution_timestamp, and outcome status.

    Returns:
        dict: Placeholder JSON payload — router is reachable and tagged
              correctly in Swagger UI.
    """
    logger.debug("GET /api/v1/agent/actions called — returning placeholder")
    return {
        "status": "not_implemented",
        "message": (
            "Action log endpoint is a future milestone.  "
            "Use POST /api/v1/agent/remediate to trigger the AI agent."
        ),
    }
