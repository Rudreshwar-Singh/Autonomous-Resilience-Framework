"""
Agent Router
============
Owns all API endpoints in the /api/v1/agent namespace.

DOMAIN RESPONSIBILITY:
    This router is the HTTP control plane for the AI Remediation Agent —
    the "brain" of the Autonomous Resilience Framework. Its responsibilities:

    - Expose a trigger endpoint so the frontend (or an internal Analysis
      call) can dispatch a remediation task for a specific incident ID.
    - Expose a query endpoint so the frontend dashboard can render the full
      chronological log of past agent decisions, prompts, and actions.

    The Agent domain (backend/agent/) will:
    1. Receive a validated IncidentContext Pydantic model (from contracts/).
    2. Package the NetworkX graph state + error traceback into a structured
       LLM prompt.
    3. Call the configured free-tier LLM (Gemini / Groq — per constraints).
    4. Strictly validate the LLM JSON response against a RemediationAction
       Pydantic model.
    5. Execute the deterministic healing action and log the outcome.

    NOTE: Per 98_project_constraints.md, no paid LLM APIs (OpenAI/Anthropic) shall
    be used. Only Gemini Free Tier, Groq, or local Ollama models.

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
    prefix="/api/v1/agent",
    tags=["Agent"],
)

# ── Placeholder Payload ───────────────────────────────────────────────────────
_PLACEHOLDER: dict[str, str] = {"status": "placeholder", "service": "agent"}


@router.get(
    "/actions",
    summary="List past agent remediation actions",
    response_description="Placeholder response — no business logic yet.",
)
async def list_agent_actions() -> dict[str, Any]:
    """
    Return the chronological log of all remediation actions executed by the
    AI Agent.

    FUTURE IMPLEMENTATION:
        Query the agent action log (in-memory list or file-based store in
        backend/logs/) and return a list of RemediationAction Pydantic models.
        Each record includes: incident_id, root_cause, action_taken,
        llm_model_used, execution_timestamp, and outcome status.

    Returns:
        dict: Placeholder JSON payload confirming the router is reachable.
    """
    logger.debug("GET /api/v1/agent/actions called — returning placeholder")
    return _PLACEHOLDER


@router.post(
    "/trigger",
    summary="Trigger the AI remediation agent for an incident",
    status_code=202,
    response_description="Placeholder response — no business logic yet.",
)
async def trigger_agent() -> dict[str, Any]:
    """
    Dispatch a remediation task to the AI Agent for a given incident.

    FUTURE IMPLEMENTATION:
        Accept a AgentTriggerRequest Pydantic model (incident_id, severity,
        affected_services). Retrieve the current NetworkX graph snapshot from
        the Analysis domain. Package everything into a structured LLM prompt
        via the Agent domain. Return a 202 Accepted immediately; the agent
        runs asynchronously and logs its outcome to backend/logs/.

    Returns:
        dict: Placeholder JSON payload confirming the router is reachable.
    """
    logger.debug("POST /api/v1/agent/trigger called — returning placeholder")
    return _PLACEHOLDER
