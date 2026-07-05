"""
Agent API Contracts
===================
Pydantic v2 data models that define the strict input/output schema for
the AI Remediation Agent's REST surface.

DOMAIN RESPONSIBILITY (01_architecture.md §2):
    This file lives in ``backend/contracts/api/`` — the **single source of
    truth** for all cross-domain communication contracts.  It must remain
    free of business logic and free of imports from other backend domains.

WHY TWO MODELS HERE?
    - ``RemediationPlan``  : The *output* contract — the exact JSON schema
      the LLM must return, validated by Pydantic before it ever reaches the
      caller.  Passing this Pydantic class to the ``google-genai`` SDK's
      ``response_schema`` parameter forces the model to produce a
      structurally correct payload at the API boundary.

    - ``RemediateRequest`` : The *input* contract — what the caller must
      POST to ``/api/v1/agent/remediate``.  It accepts the raw
      ``GraphPayload`` dict (Phase 6 output) plus an optional traceback
      string, giving the agent all context it needs.

PYDANTIC v2 NOTES (99_ai_rules.md):
    - Use ``model_validate()`` not ``parse_obj()``.
    - Use ``model_dump()`` not ``dict()``.
    - ``Field(description=...)`` drives the OpenAPI docs automatically.

REFERENCES:
    - 01_architecture.md §2 (contracts/ is the cross-domain boundary)
    - 01_architecture.md §5 (Fail Fast — validate at every boundary)
    - 98_project_constraints.md (Pydantic v2, no paid LLM APIs)
    - 99_ai_rules.md (strict typing, Pydantic v2 syntax)
"""

from pydantic import BaseModel, ConfigDict, Field


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT CONTRACT — LLM Response Schema
# ══════════════════════════════════════════════════════════════════════════════


class RemediationPlan(BaseModel):
    """
    The strict, validated output produced by the AI Remediation Agent.

    This model is passed directly to the ``google-genai`` SDK's
    ``response_schema`` parameter, which instructs the Gemini model to emit
    a JSON payload that conforms exactly to this schema.  Pydantic then
    validates the parsed response a second time, giving us a double-checked,
    type-safe object that the rest of the system can consume without
    defensive null-checks.

    Attributes:
        root_cause:       A clear, technical explanation of the detected
                          failure — written at an SRE level (e.g., naming
                          the specific service, error code, and propagation
                          path).
        impacted_nodes:   IDs of all services in the blast radius — i.e.,
                          every node whose health is degraded as a direct or
                          indirect consequence of the root cause.
        suggested_action: A step-by-step, numbered remediation plan that an
                          on-call engineer (or future automation layer) can
                          execute verbatim.
        target_service:   The single internal service name that the healing
                          action must be applied to first (e.g.,
                          ``"User-DB"``).  Used by the deterministic action
                          executor in future phases.
    """

    # Allow extra fields from the LLM to be silently ignored rather than
    # raising a ValidationError — makes the contract forward-compatible if
    # the model adds explanatory keys we did not request.
    model_config = ConfigDict(extra="ignore", strict=False)

    root_cause: str = Field(
        ...,
        description=(
            "A clear, technical explanation of the root cause of the "
            "observed system failure, naming the specific service, error "
            "code, and propagation path."
        ),
        min_length=10,
    )

    impacted_nodes: list[str] = Field(
        ...,
        description=(
            "Ordered list of service IDs (node names) that are degraded or "
            "failing as a consequence of the root cause.  Represents the "
            "blast radius of the incident."
        ),
        min_length=1,
    )

    suggested_action: str = Field(
        ...,
        description=(
            "A numbered, step-by-step remediation plan an on-call SRE "
            "or automated executor can follow to restore service health."
        ),
        min_length=10,
    )

    target_service: str = Field(
        ...,
        description=(
            "The single internal service name that the primary healing "
            "action must target first (e.g., 'User-DB', 'Auth-Service')."
        ),
        min_length=1,
    )


# ══════════════════════════════════════════════════════════════════════════════
# INPUT CONTRACT — REST Request Body
# ══════════════════════════════════════════════════════════════════════════════


class RemediateRequest(BaseModel):
    """
    The validated request body for ``POST /api/v1/agent/remediate``.

    Callers (the frontend dashboard or an internal Analysis domain trigger)
    must supply the current NetworkX graph snapshot from Phase 6 alongside
    an optional raw error traceback to give the LLM maximum diagnostic context.

    Attributes:
        graph_payload:   The exact JSON dict produced by
                         ``GraphAnalyzer.export_payload().model_dump()``.
                         Must contain ``nodes``, ``edges``, and ``meta`` keys.
        error_traceback: An optional raw Python / service exception traceback
                         captured at the failure point.  Providing this
                         dramatically improves root-cause precision because
                         the LLM can correlate the stack trace with the
                         graph topology.
    """

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields — Fail Fast

    graph_payload: dict = Field(
        ...,
        description=(
            "The GraphPayload JSON dict from the Phase 6 NetworkX analyzer. "
            "Must contain 'nodes' (with error_metadata), 'edges', and 'meta'."
        ),
    )

    error_traceback: str | None = Field(
        default=None,
        description=(
            "Optional raw exception traceback captured at the failure site. "
            "Providing this string dramatically improves LLM root-cause precision."
        ),
    )
