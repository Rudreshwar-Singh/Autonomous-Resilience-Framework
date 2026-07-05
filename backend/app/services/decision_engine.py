"""
Decision Engine Service
=======================
The AI reasoning layer of the Autonomous Resilience Framework.

DOMAIN RESPONSIBILITY (01_architecture.md §2 — Agent domain):
    This service is the **brain** of the system.  It ingests the JSON DAG
    produced by Phase 6 (NetworkX ``GraphAnalyzer``) and the raw error
    traceback, then queries Google Gemini to produce a deterministic,
    strictly-typed ``RemediationPlan``.

    It does NOT:
    - Handle HTTP requests (that is the router's job).
    - Contain graph-traversal logic (that belongs in ``graph_analyzer.py``).
    - Maintain state across calls (stateless, instantiated once at startup).

AI PROVIDER CHOICE (98_project_constraints.md):
    - Provider: Google Gemini (free-tier) via the NEW ``google-genai`` SDK.
      ``from google import genai``  ← this is the correct 2024+ import.
      Do NOT use the legacy ``google-generativeai`` package.
    - Model: ``gemini-2.5-flash`` (default) — best speed/quality ratio on
      the free tier and the first Gemini model with native structured-output
      enforcement.

STRUCTURED OUTPUT DESIGN (the critical design pattern):
    Instead of prompting the model to "respond in JSON" and then regex-
    parsing the response (brittle), we pass the ``RemediationPlan`` Pydantic
    class directly to the SDK's ``response_schema`` parameter.  This forces
    Gemini to generate a response that matches the schema at the model level,
    before any Python code even sees the bytes.  Pydantic then validates it a
    *second* time, giving us a double-checked, type-safe object.

    WHY THIS MATTERS FOR AUTONOMOUS AGENTS:
        In a self-healing system, a malformed LLM response does not just mean
        a bad UI render — it can mean the wrong service gets restarted, or the
        blast radius is misidentified, causing a wider outage.  Schema
        enforcement at the LLM boundary converts a probabilistic text model
        into a deterministic function with a guaranteed return type.

REFERENCES:
    - 01_architecture.md §3 (Agent domain: step 4 Diagnosis, step 5 Mitigation)
    - 01_architecture.md §5 (Explainability — all complex logic must be
      heavily commented and easy to whiteboard)
    - 98_project_constraints.md (No paid APIs; No LangGraph; Pydantic v2)
    - 99_ai_rules.md (Strict typing, structured logging, try/except)
    - google-genai SDK docs: https://googleapis.github.io/python-genai/
"""

import json
import logging
import os
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from backend.contracts.api.agent import RemediationPlan

# ── Module logger ──────────────────────────────────────────────────────────────
# Inherits the JSON-structured handler configured by main.py's lifespan,
# so every log line from this module is machine-parseable.
logger: logging.Logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

# WHY A SEPARATE CONSTANT FOR THE SYSTEM PROMPT?
#   Keeping the system prompt here (not buried inside the method) makes it
#   trivially easy to iterate on, version-control independently, and explain
#   in a technical interview without scrolling through business logic.
_SYSTEM_PROMPT: str = """
You are an expert Site Reliability Engineer (SRE) and distributed systems
failure analyst embedded in an Autonomous Resilience Framework.

Your job is to analyse the provided service dependency graph — a directed
acyclic graph (DAG) produced by a NetworkX topology analyser — and return a
precise, actionable RemediationPlan.

The graph JSON you receive contains:
  - "nodes": each service node with its health status ("success"/"failed"/
    "degraded"), call_count, failure_count, and error_metadata (error_code,
    message, latency_ms, extra context).
  - "edges": directed caller → callee relationships with edge weights
    (number of trace hops).
  - "meta": pre-computed statistics including root_cause_candidate (the
    failed node with the fewest upstream callers) and blast_radius (all
    ancestor services impacted).

ANALYSIS APPROACH — think step by step:
  1. Identify the root cause: look for the failed node with the lowest
     in-degree (fewest callers) — this is the origin of the cascade.
  2. Trace propagation: follow the DAG edges upward from the root cause
     to identify every impacted service.
  3. Compose a concrete remediation: reference the specific error_code and
     latency data from error_metadata in your response.
  4. Name the target_service: the single service where the first healing
     action must be applied.

RULES:
  - Be technical and specific. Name services, error codes, and latency values.
  - Do NOT use vague language like "check the logs" without specifics.
  - The suggested_action must be a numbered list of concrete steps.
  - impacted_nodes must be a list of exact service ID strings from the graph.
"""


# ══════════════════════════════════════════════════════════════════════════════
# DECISION ENGINE CLASS
# ══════════════════════════════════════════════════════════════════════════════


class DecisionEngine:
    """
    Stateful service that wraps the Google Gemini LLM client and exposes a
    single public method: ``analyze_fault_graph``.

    INSTANTIATION PATTERN:
        Create once at application startup (in main.py's lifespan context)
        and attach to ``app.state.decision_engine``.  This reuses the
        underlying HTTP connection pool instead of creating a new client
        per request — exactly the same pattern used by ``KafkaProducerService``.

    THREAD SAFETY:
        ``genai.Client`` is documented as thread-safe for concurrent calls.
        A single ``DecisionEngine`` instance can serve multiple simultaneous
        FastAPI requests without locking.

    INTERVIEW WHITEBOARD SUMMARY:
        Input  → GraphPayload dict (nodes, edges, meta) + optional traceback
        Step 1 → Build a structured text prompt from the graph JSON
        Step 2 → Send to Gemini with response_schema=RemediationPlan
        Step 3 → SDK enforces schema; Pydantic validates the result
        Output → RemediationPlan (root_cause, impacted_nodes,
                  suggested_action, target_service)
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        """
        Initialise the Gemini client.

        Args:
            api_key: The Google Gemini API key.  Per 98_project_constraints.md,
                     this must be a free-tier key from environment variables —
                     never hard-coded or committed to source control.
            model:   The Gemini model identifier.  Defaults to
                     ``gemini-2.5-flash``.

        Raises:
            ValueError: If ``api_key`` is empty — we fail fast rather than
                        silently sending unauthenticated requests that will
                        always 401.
        """
        if not api_key:
            raise ValueError(
                "DecisionEngine requires a GEMINI_API_KEY.  "
                "Set it via environment variable or .env file.  "
                "Per 98_project_constraints.md, use the free-tier key only."
            )

        # ``genai.Client`` is the top-level entry point for the new SDK.
        # It manages the underlying HTTP session and authentication.
        self._client: genai.Client = genai.Client(api_key=api_key)
        self._model: str = model

        logger.info(
            "DecisionEngine initialised — model=%s",
            self._model,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def analyze_fault_graph(
        self,
        graph_payload: dict[str, Any],
        error_traceback: str | None = None,
    ) -> RemediationPlan:
        """
        Core reasoning method: analyse the dependency graph and return a
        deterministic, schema-validated remediation plan.

        ALGORITHM:
            1. Validate that the graph payload has the expected top-level keys
               (nodes, edges, meta) — fail fast at our boundary.
            2. Serialise the graph dict to an indented JSON string so the LLM
               receives a human-readable topology view.
            3. Append the optional error traceback if provided.
            4. Call the Gemini API with ``response_schema=RemediationPlan`` so
               the SDK enforces structural correctness before we parse.
            5. Pydantic validates the returned object a second time.
            6. Return the validated ``RemediationPlan``.

        WHY TWO LAYERS OF VALIDATION?
            The SDK's ``response_schema`` coerces the model output at the
            network boundary.  Pydantic's ``model_validate()`` then verifies
            that the parsed Python object satisfies our field constraints
            (e.g., ``min_length`` on ``root_cause``).  Two independent checks
            mean a corrupted or truncated API response cannot produce an
            invalid plan that silently propagates.

        Args:
            graph_payload:   The exact dict produced by
                             ``GraphPayload.model_dump()``.  Must contain
                             ``nodes``, ``edges``, and ``meta`` keys.
            error_traceback: An optional raw exception string captured at the
                             failure site.  Providing this improves root-cause
                             precision significantly.

        Returns:
            A fully validated ``RemediationPlan`` instance.

        Raises:
            ValueError:           If ``graph_payload`` is missing required keys.
            genai_errors.APIError: Re-raised after logging if Gemini returns a
                                   non-2xx response (rate limit, quota, etc.).
            ValidationError:      Re-raised after logging if the LLM response
                                  passes the SDK check but fails Pydantic
                                  field-level constraints.
        """
        # ── Step 1: Validate input structure ──────────────────────────────
        # We check for required keys here rather than letting a KeyError
        # surface later with a cryptic traceback.
        required_keys = {"nodes", "edges", "meta"}
        missing = required_keys - set(graph_payload.keys())
        if missing:
            raise ValueError(
                f"graph_payload is missing required keys: {missing}. "
                f"Expected output from GraphAnalyzer.export_payload().model_dump()."
            )

        # ── Step 2: Serialise graph to a readable JSON string ─────────────
        # ``default=str`` handles non-JSON-serialisable values (e.g., enums,
        # datetime objects) by converting them to their string representation.
        graph_json_str: str = json.dumps(graph_payload, indent=2, default=str)

        # ── Step 3: Build the user prompt ─────────────────────────────────
        # The system prompt (above) provides role and instructions.
        # The user prompt provides the concrete data for this specific call.
        user_prompt_parts: list[str] = [
            "## Service Dependency Graph (JSON)\n",
            "```json",
            graph_json_str,
            "```",
        ]

        if error_traceback:
            user_prompt_parts += [
                "\n## Raw Error Traceback\n",
                "```",
                error_traceback.strip(),
                "```",
            ]

        user_prompt_parts.append(
            "\nAnalyse the graph above and return a RemediationPlan JSON object."
        )

        user_prompt: str = "\n".join(user_prompt_parts)

        logger.info(
            "Sending fault graph to Gemini — model=%s nodes=%d edges=%d",
            self._model,
            len(graph_payload.get("nodes", [])),
            len(graph_payload.get("edges", [])),
        )

        # ── Step 4: Call Gemini with structured output enforcement ────────
        # KEY DESIGN DECISION: ``response_schema=RemediationPlan`` tells the
        # Gemini API to constrain its token generation to the JSON Schema
        # derived from our Pydantic model.  This is fundamentally different
        # from asking the model to "respond in JSON" — the constraint is
        # enforced at the sampling level, not the parsing level.
        #
        # ``response_mime_type="application/json"`` is required alongside
        # ``response_schema`` to activate constrained decoding mode.
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=user_prompt)],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    # Passing the Pydantic class directly — the SDK derives
                    # the JSON Schema automatically from the model's fields.
                    response_schema=RemediationPlan,
                    # Temperature 0 is intentional: this is an analytical task,
                    # not a creative one.  We want deterministic, reproducible
                    # output — essential for a self-healing system where the
                    # same fault should always produce the same remediation.
                    temperature=0.0,
                ),
            )

        except genai_errors.APIError as exc:
            # Network errors, rate limits (429), quota exceeded (503), etc.
            # Log with full context then re-raise so the router can return a
            # meaningful HTTP 503 to the client instead of a raw 500.
            logger.error(
                "Gemini API call failed — model=%s status=%s message=%s",
                self._model,
                getattr(exc, "status_code", "unknown"),
                str(exc),
            )
            raise

        # ── Step 5: Extract and validate the response ─────────────────────
        # ``response.parsed`` is populated by the SDK when ``response_schema``
        # was provided — it returns the already-parsed Pydantic model instance.
        # We still call ``model_validate()`` as a defensive second pass.
        raw_text: str = response.text or ""
        logger.debug("Raw Gemini response text — length=%d chars", len(raw_text))

        try:
            # Prefer the SDK's pre-parsed result if available; fall back to
            # manual JSON parsing.  This handles SDK version differences
            # gracefully without failing.
            if hasattr(response, "parsed") and response.parsed is not None:
                plan: RemediationPlan = RemediationPlan.model_validate(
                    response.parsed
                    if isinstance(response.parsed, dict)
                    else response.parsed.model_dump()
                )
            else:
                # Manual fallback: parse the JSON text and validate.
                raw_dict: dict = json.loads(raw_text)
                plan = RemediationPlan.model_validate(raw_dict)

        except (json.JSONDecodeError, ValidationError) as exc:
            # The model passed the SDK's schema check but failed our Pydantic
            # field constraints (e.g., min_length).  Log and re-raise.
            logger.error(
                "RemediationPlan validation failed — raw_response=%s error=%s",
                raw_text[:500],  # Truncate to avoid flooding logs
                str(exc),
            )
            raise

        logger.info(
            "RemediationPlan generated — root_cause=%r target_service=%r "
            "impacted_nodes_count=%d",
            plan.root_cause[:80],  # Truncate for log readability
            plan.target_service,
            len(plan.impacted_nodes),
        )

        return plan


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION (for router injection)
# ══════════════════════════════════════════════════════════════════════════════


def analyze_fault_graph(
    graph_payload: dict[str, Any],
    error_traceback: str | None = None,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
) -> RemediationPlan:
    """
    Convenience wrapper: instantiate ``DecisionEngine`` and call
    ``analyze_fault_graph`` in a single step.

    Designed for one-off calls (e.g., the ``__main__`` test harness or
    a FastAPI dependency factory).  For high-throughput production use,
    prefer creating a shared ``DecisionEngine`` instance in the lifespan
    context and attaching it to ``app.state``.

    Args:
        graph_payload:   GraphPayload dict from ``GraphAnalyzer``.
        error_traceback: Optional exception traceback string.
        api_key:         Gemini API key.  Defaults to ``GEMINI_API_KEY``
                         environment variable if not provided.
        model:           Gemini model identifier. Defaults to
                         ``gemini-2.5-flash``.

    Returns:
        A validated ``RemediationPlan``.

    Raises:
        ValueError:  If no API key is found in args or environment.
    """
    resolved_key: str = api_key or os.environ.get("GEMINI_API_KEY", "")
    engine = DecisionEngine(api_key=resolved_key, model=model)
    return engine.analyze_fault_graph(graph_payload, error_traceback)


# ══════════════════════════════════════════════════════════════════════════════
# TEST HARNESS — Run directly to verify LLM reasoning and schema output
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Self-contained integration test harness.

    HOW TO RUN (from the project root, with your API key set):
        Windows PowerShell:
            $env:GEMINI_API_KEY = "AIza..."
            python -m backend.app.services.decision_engine

    SCENARIO: Cascading failure — DB timeout propagates through auth to gateway.
        Client → API-Gateway (OK)
        API-Gateway → Auth-Service (cascaded 500)
        Auth-Service → User-DB (ROOT CAUSE — DB_TIMEOUT_ERROR, 30042ms)
        API-Gateway → Notification-Service (DEGRADED — HIGH_LATENCY_WARNING)

    EXPECTED OUTPUT:
        - root_cause     : identifies User-DB as the origin (DB_TIMEOUT_ERROR)
        - target_service : "User-DB"
        - impacted_nodes : ["Auth-Service", "API-Gateway", ...]
        - suggested_action: numbered steps referencing DB_TIMEOUT_ERROR and
                            the 30042ms latency
    """
    import sys

    # Use the rich library (already in requirements.txt) for clean terminal output
    try:
        from rich import print as rprint
        from rich.panel import Panel
        from rich.syntax import Syntax
    except ImportError:
        rprint = print  # type: ignore[assignment]

    print("\n" + "=" * 72)
    print("  ARF Phase 7 — DecisionEngine Test Harness")
    print("  Scenario: Cascading DB Timeout (Client → Gateway → Auth → DB)")
    print("=" * 72 + "\n")

    # ── Mock Phase 6 GraphPayload (exact output format from GraphAnalyzer) ──
    # This simulates the dict produced by GraphPayload.model_dump() after
    # processing the trace events shown in graph_analyzer.py's __main__ block.
    MOCK_GRAPH_PAYLOAD: dict[str, Any] = {
        "nodes": [
            {
                "id": "Client",
                "status": "success",
                "error_metadata": None,
                "call_count": 0,
                "failure_count": 0,
            },
            {
                "id": "API-Gateway",
                "status": "failed",
                "error_metadata": {
                    "error_code": "500_INTERNAL_SERVER_ERROR",
                    "message": "Dependency 'Auth-Service' failed to respond within SLO",
                    "latency_ms": 30100.2,
                    "extra": {"upstream_error": "DB_TIMEOUT_ERROR"},
                },
                "call_count": 1,
                "failure_count": 1,
            },
            {
                "id": "Auth-Service",
                "status": "failed",
                "error_metadata": {
                    "error_code": "500_INTERNAL_SERVER_ERROR",
                    "message": "Dependency 'User-DB' failed to respond within SLO",
                    "latency_ms": 30100.2,
                    "extra": {"upstream_error": "DB_TIMEOUT_ERROR"},
                },
                "call_count": 2,
                "failure_count": 2,
            },
            {
                "id": "User-DB",
                "status": "failed",
                "error_metadata": {
                    "error_code": "DB_TIMEOUT_ERROR",
                    "message": "Connection timeout while querying User-DB replica",
                    "latency_ms": 30042.7,
                    "extra": {"db_host": "user-db-primary:5432", "retry_count": 3},
                },
                "call_count": 1,
                "failure_count": 1,
            },
            {
                "id": "Notification-Service",
                "status": "degraded",
                "error_metadata": {
                    "error_code": "HIGH_LATENCY_WARNING",
                    "message": "Response latency 4200ms exceeds 1000ms SLO threshold",
                    "latency_ms": 4200.0,
                    "extra": {},
                },
                "call_count": 1,
                "failure_count": 1,
            },
        ],
        "edges": [
            {"source": "Client", "target": "API-Gateway", "weight": 1},
            {"source": "API-Gateway", "target": "Auth-Service", "weight": 2},
            {"source": "Auth-Service", "target": "User-DB", "weight": 1},
            {"source": "API-Gateway", "target": "Notification-Service", "weight": 1},
        ],
        "meta": {
            "total_nodes": 5,
            "total_edges": 4,
            "failed_node_count": 3,
            "root_cause_candidate": "User-DB",
            "blast_radius": ["Auth-Service", "API-Gateway"],
        },
    }

    # Simulated raw error traceback captured from the Auth-Service pod logs.
    MOCK_TRACEBACK: str = """
Traceback (most recent call last):
  File "/app/services/auth_service.py", line 142, in authenticate_user
    user = db_session.query(User).filter(User.id == user_id).one()
  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/query.py", line 2800, in one
    raise NoResultFound("No row was found when one was required")
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server:
    Connection timed out
    Is the server running on host "user-db-primary" (10.0.1.15) and accepting
    TCP/IP connections on port 5432?
[Error Code: DB_TIMEOUT_ERROR | Retries: 3 | Latency: 30042ms]
""".strip()

    # ── Run the engine ──────────────────────────────────────────────────────
    print("[1/3] Resolving GEMINI_API_KEY from environment...")
    resolved_api_key: str = os.environ.get("GEMINI_API_KEY", "")

    if not resolved_api_key:
        print(
            "\n[ERROR] GEMINI_API_KEY is not set.\n"
            "  Set it first:\n"
            "    PowerShell: $env:GEMINI_API_KEY = 'AIza...'\n"
            "    Bash/WSL:   export GEMINI_API_KEY='AIza...'\n"
        )
        sys.exit(1)

    print("[2/3] Sending fault graph to Gemini (gemini-2.5-flash)...")
    print("      This may take a few seconds on the free tier...\n")

    try:
        plan: RemediationPlan = analyze_fault_graph(
            graph_payload=MOCK_GRAPH_PAYLOAD,
            error_traceback=MOCK_TRACEBACK,
            api_key=resolved_api_key,
            model="gemini-2.5-flash",
        )
    except ValueError as exc:
        print(f"[ERROR] Configuration error: {exc}")
        sys.exit(1)
    except genai_errors.APIError as exc:
        print(f"[ERROR] Gemini API returned an error: {exc}")
        sys.exit(1)
    except (json.JSONDecodeError, ValidationError) as exc:
        print(f"[ERROR] RemediationPlan schema validation failed: {exc}")
        sys.exit(1)

    # ── Print the validated output ──────────────────────────────────────────
    print("[3/3] RemediationPlan received and validated ✓\n")
    print("=" * 72)
    print("  VALIDATED RemediationPlan JSON")
    print("=" * 72)
    plan_json: str = plan.model_dump_json(indent=2)
    print(plan_json)
    print("=" * 72)

    print("\nFIELD SUMMARY:")
    print(f"  Root Cause      : {plan.root_cause[:100]}...")
    print(f"  Target Service  : {plan.target_service}")
    print(f"  Impacted Nodes  : {plan.impacted_nodes}")
    print(f"  Action Preview  : {plan.suggested_action[:120]}...")

    print("\n" + "=" * 72)
    print("  [OK] Phase 7 DecisionEngine schema verification complete.")
    print("       The LLM returned a valid, Pydantic-validated RemediationPlan.")
    print("=" * 72 + "\n")
