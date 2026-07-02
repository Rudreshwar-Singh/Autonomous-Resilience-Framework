"""
Incident Router
===============
Owns all API endpoints in the /api/v1/incident namespace.

DOMAIN RESPONSIBILITY:
    This router is the HTTP boundary for the Incident domain. In future
    phases it will expose endpoints to:
    - List active incidents detected by the Analysis domain.
    - Retrieve the full forensic timeline for a specific incident.
    - Acknowledge or close an incident after autonomous remediation.

CURRENT PHASE (MVP Skeleton):
    All endpoints return a strictly typed placeholder payload to prove the
    routing layer is wired correctly before business logic is implemented.
    No database queries, no domain imports — the contract surface only.
"""

import logging
from typing import Any

from fastapi import APIRouter

# ── Module logger ─────────────────────────────────────────────────────────────
# Inherits the structured-JSON handler configured in lifespan (main.py).
logger: logging.Logger = logging.getLogger(__name__)

# ── Router Definition ─────────────────────────────────────────────────────────
# prefix  → prepended to every route path declared below.
# tags    → groups all routes under the "Incident" section in Swagger UI.
router: APIRouter = APIRouter(
    prefix="/api/v1/incident",
    tags=["Incident"],
)

# ── Placeholder Payload ───────────────────────────────────────────────────────
# Centralised so that every placeholder endpoint returns an identical,
# deterministic payload — easy to assert against in future integration tests.
_PLACEHOLDER: dict[str, str] = {"status": "placeholder", "service": "incident"}


@router.get(
    "/",
    summary="List all active incidents",
    response_description="Placeholder response — no business logic yet.",
)
async def list_incidents() -> dict[str, Any]:
    """
    Return a paginated list of all active incidents.

    FUTURE IMPLEMENTATION:
        Query the Analysis domain for nodes whose health score has breached
        the configured degradation threshold and return them as IncidentRecord
        Pydantic models. Supports filtering by severity and service name.

    Returns:
        dict: Placeholder JSON payload confirming the router is reachable.
    """
    logger.debug("GET /api/v1/incident/ called — returning placeholder")
    return _PLACEHOLDER


@router.post(
    "/",
    summary="Open a new incident manually",
    status_code=201,
    response_description="Placeholder response — no business logic yet.",
)
async def create_incident() -> dict[str, Any]:
    """
    Manually open a new incident record.

    FUTURE IMPLEMENTATION:
        Accept an IncidentCreateRequest Pydantic model containing the
        affected service name, detected fault type, and initial severity.
        Persist the record and trigger the Analysis domain to update the
        dependency graph accordingly.

    Returns:
        dict: Placeholder JSON payload confirming the router is reachable.
    """
    logger.debug("POST /api/v1/incident/ called — returning placeholder")
    return _PLACEHOLDER
