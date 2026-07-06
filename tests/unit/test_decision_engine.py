"""
Decision Engine Unit Tests
===========================
Phase 8: Test Harness — Task 2.

PURPOSE:
    Validate that DecisionEngine behaves correctly in complete isolation from
    the real Google Gemini API.  Zero HTTP requests are made to any external
    service during these tests.

MOCKING STRATEGY:
    We patch ``google.genai.Client`` at the point of import inside
    ``decision_engine.py``.  The mock replaces the entire Gemini client,
    allowing us to control exactly what the "API" returns for each test.

    This achieves three critical properties for CI pipelines:
    1. SPEED    — no network round-trips; tests run in <10ms.
    2. RELIABILITY — no dependency on API quota, rate limits, or model
                    availability; tests always pass if our code is correct.
    3. DETERMINISM — we control the mock response, so we can test both
                     success and every failure mode exhaustively.

WHAT IS TESTED:
    Test 1 — SUCCESS PATH:
        Inject a mock NetworkX graph payload and mock the LLM returning a
        valid JSON string that matches the RemediationPlan schema.  Verify:
        - No exceptions are raised.
        - The returned object is a correctly typed RemediationPlan instance.
        - All four required fields (root_cause, target_service,
          impacted_nodes, suggested_action) are populated from the mock.

    Test 2 — API FAILURE (genai_errors.APIError):
        Mock the Gemini client raising an APIError (e.g., rate limit 429,
        quota exceeded 503).  Verify the engine re-raises the error after
        logging it — never swallowing it silently.

    Test 3 — MALFORMED JSON RESPONSE:
        Mock the LLM returning a syntactically broken JSON string.  Verify
        the JSONDecodeError is caught, logged, and re-raised — not silently
        ignored.

    Test 4 — PYDANTIC VALIDATION FAILURE:
        Mock the LLM returning structurally valid JSON that fails Pydantic
        field constraints (e.g., root_cause too short).  Verify
        ValidationError is caught, logged, and re-raised.

    Test 5 — MISSING GRAPH KEYS:
        Pass an incomplete graph_payload (missing 'meta' key).  Verify
        the engine raises ValueError immediately — Fail Fast boundary.

    Test 6 — EMPTY API KEY:
        Verify DecisionEngine raises ValueError on instantiation when
        api_key is empty — prevents silent unauthenticated requests.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

# ── Project imports ────────────────────────────────────────────────────────────
from backend.app.services.decision_engine import DecisionEngine
from backend.contracts.api.agent import RemediationPlan


# ══════════════════════════════════════════════════════════════════════════════
# SHARED FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def mock_graph_payload() -> dict[str, Any]:
    """
    A realistic GraphPayload dict matching the exact structure produced by
    Phase 6 GraphAnalyzer.export_payload().model_dump().

    Scenario: DB timeout cascades through Auth-Service to API-Gateway.
    """
    return {
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
                    "message": "Dependency Auth-Service failed to respond within SLO",
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
                    "message": "Dependency User-DB failed to respond within SLO",
                    "latency_ms": 30042.7,
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
        ],
        "edges": [
            {"source": "Client", "target": "API-Gateway", "weight": 1},
            {"source": "API-Gateway", "target": "Auth-Service", "weight": 2},
            {"source": "Auth-Service", "target": "User-DB", "weight": 1},
        ],
        "meta": {
            "total_nodes": 4,
            "total_edges": 3,
            "failed_node_count": 3,
            "root_cause_candidate": "User-DB",
            "blast_radius": ["Auth-Service", "API-Gateway"],
        },
    }


@pytest.fixture()
def valid_remediation_plan_json() -> str:
    """
    A valid JSON string matching the RemediationPlan schema.
    Mocks what Gemini would return in the success case.
    """
    plan = {
        "root_cause": (
            "User-DB (user-db-primary:5432) timed out after 30042ms with error "
            "DB_TIMEOUT_ERROR after 3 retries, causing a cascading failure through "
            "Auth-Service and API-Gateway."
        ),
        "target_service": "User-DB",
        "impacted_nodes": ["Auth-Service", "API-Gateway"],
        "suggested_action": (
            "1. Verify User-DB primary connectivity: "
            "`psql -h user-db-primary -p 5432 -U admin`.\n"
            "2. Check DB connection pool saturation via Prometheus metrics.\n"
            "3. Restart User-DB replica if primary is unresponsive.\n"
            "4. Scale up Auth-Service connection pool timeout from 30s to 60s.\n"
            "5. Monitor API-Gateway error rate until it drops below 1%."
        ),
    }
    return json.dumps(plan)


@pytest.fixture()
def decision_engine_with_mock_client() -> tuple[DecisionEngine, MagicMock]:
    """
    Return a (DecisionEngine, mock_genai_client_instance) tuple.

    The underlying genai.Client is fully mocked — no HTTP connection is made.
    """
    with patch("backend.app.services.decision_engine.genai") as mock_genai:
        mock_client_instance = MagicMock()
        mock_genai.Client.return_value = mock_client_instance

        engine = DecisionEngine(api_key="fake-api-key-for-testing")
        yield engine, mock_client_instance


# ══════════════════════════════════════════════════════════════════════════════
# TEST CLASS
# ══════════════════════════════════════════════════════════════════════════════


class TestDecisionEngineSuccess:
    """
    Task 2 — Test 1: Verify the success path end-to-end.

    The LLM mock returns a valid JSON RemediationPlan; we verify that
    Pydantic parses it correctly into a typed object.
    """

    def test_analyze_fault_graph_returns_valid_remediation_plan(
        self,
        mock_graph_payload: dict[str, Any],
        valid_remediation_plan_json: str,
    ) -> None:
        """
        GIVEN  a valid graph_payload dict (Phase 6 output)
        AND    the Gemini API mock returns a conforming RemediationPlan JSON
        WHEN   DecisionEngine.analyze_fault_graph() is called
        THEN   a fully validated RemediationPlan is returned with no exceptions.

        This verifies the double-validation design: SDK schema check +
        Pydantic model_validate() both pass on a well-formed response.
        """
        with patch("backend.app.services.decision_engine.genai") as mock_genai:
            # Build a mock response object that mimics what the SDK returns.
            mock_response = MagicMock()
            mock_response.text = valid_remediation_plan_json
            # ``response.parsed`` is None here — exercises the JSON fallback path.
            mock_response.parsed = None

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            engine = DecisionEngine(api_key="fake-api-key-for-testing")
            plan: RemediationPlan = engine.analyze_fault_graph(
                graph_payload=mock_graph_payload,
                error_traceback="DB_TIMEOUT_ERROR after 3 retries",
            )

        # Verify the return type.
        assert isinstance(plan, RemediationPlan), (
            f"Expected RemediationPlan instance, got {type(plan)}"
        )

        # Verify all four required fields are populated and non-empty.
        assert len(plan.root_cause) >= 10, "root_cause must be at least 10 chars"
        assert plan.target_service == "User-DB"
        assert "Auth-Service" in plan.impacted_nodes
        assert "API-Gateway" in plan.impacted_nodes
        assert len(plan.suggested_action) >= 10

    def test_analyze_fault_graph_uses_sdk_parsed_result_when_available(
        self,
        mock_graph_payload: dict[str, Any],
        valid_remediation_plan_json: str,
    ) -> None:
        """
        When ``response.parsed`` is a dict (SDK parsed the response),
        the engine must use it directly instead of calling ``json.loads()``.

        This tests the primary code path (not the fallback).
        """
        with patch("backend.app.services.decision_engine.genai") as mock_genai:
            plan_dict = json.loads(valid_remediation_plan_json)

            mock_response = MagicMock()
            mock_response.text = valid_remediation_plan_json
            # Simulate the SDK returning a pre-parsed dict via response.parsed.
            mock_response.parsed = plan_dict

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            engine = DecisionEngine(api_key="fake-api-key-for-testing")
            plan: RemediationPlan = engine.analyze_fault_graph(
                graph_payload=mock_graph_payload,
            )

        assert isinstance(plan, RemediationPlan)
        assert plan.target_service == "User-DB"


class TestDecisionEngineFailureCases:
    """
    Task 2 — Test 2: Verify all error / edge-case paths.

    Each test mocks a different failure mode and asserts the correct
    exception propagates — never a silent swallow.
    """

    def test_api_error_is_re_raised(
        self,
        mock_graph_payload: dict[str, Any],
    ) -> None:
        """
        GIVEN  the Gemini API raises APIError (rate limit 429, quota 503, etc.)
        WHEN   analyze_fault_graph() is called
        THEN   the APIError is logged and re-raised — not swallowed.

        In production, the router catches this and returns HTTP 503 to the
        client with a human-readable error message.
        """
        from google.genai import errors as genai_errors

        # APIError in google-genai SDK v2.x requires (message, response_json).
        api_error = genai_errors.APIError(
            "429 Resource exhausted: quota exceeded",
            {"error": {"code": 429, "message": "quota exceeded", "status": "RESOURCE_EXHAUSTED"}},
        )

        with patch("backend.app.services.decision_engine.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = api_error
            mock_genai.Client.return_value = mock_client
            mock_genai.errors = genai_errors  # Ensure the module ref is correct.

            engine = DecisionEngine(api_key="fake-api-key-for-testing")

            with pytest.raises(genai_errors.APIError):
                engine.analyze_fault_graph(graph_payload=mock_graph_payload)


    def test_malformed_json_response_raises_json_decode_error(
        self,
        mock_graph_payload: dict[str, Any],
    ) -> None:
        """
        GIVEN  the LLM returns syntactically broken JSON (truncated response,
               network corruption, or model hallucination)
        WHEN   analyze_fault_graph() processes the response
        THEN   a JSONDecodeError is caught, logged, and re-raised — never
               silently ignored.

        Per 99_ai_rules.md: "Never silently ignore errors".
        """
        with patch("backend.app.services.decision_engine.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.text = '{"root_cause": "DB timeout", BROKEN JSON!!!'
            mock_response.parsed = None

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            engine = DecisionEngine(api_key="fake-api-key-for-testing")

            with pytest.raises(json.JSONDecodeError):
                engine.analyze_fault_graph(graph_payload=mock_graph_payload)

    def test_pydantic_validation_failure_raises_validation_error(
        self,
        mock_graph_payload: dict[str, Any],
    ) -> None:
        """
        GIVEN  the LLM returns valid JSON but violates Pydantic field
               constraints (e.g., root_cause is fewer than 10 chars)
        WHEN   analyze_fault_graph() validates the response
        THEN   a ValidationError is caught, logged, and re-raised.

        This tests the second validation layer (Pydantic model_validate())
        that catches issues the SDK's schema check might miss — the
        "double-checked" design described in decision_engine.py.
        """
        invalid_plan = {
            "root_cause": "short",        # Violates min_length=10
            "target_service": "User-DB",
            "impacted_nodes": ["Auth-Service"],
            "suggested_action": "Restart the service immediately and monitor.",
        }

        with patch("backend.app.services.decision_engine.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.text = json.dumps(invalid_plan)
            mock_response.parsed = None

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            engine = DecisionEngine(api_key="fake-api-key-for-testing")

            with pytest.raises(ValidationError):
                engine.analyze_fault_graph(graph_payload=mock_graph_payload)

    def test_missing_graph_keys_raises_value_error(self) -> None:
        """
        GIVEN  graph_payload is missing required top-level keys
               (e.g., 'meta' is absent)
        WHEN   analyze_fault_graph() is called
        THEN   ValueError is raised immediately — before any LLM call is made.

        This is the Fail-Fast boundary from 01_architecture.md §5:
        all external inputs must be validated at the domain boundary.
        The LLM must never receive malformed input.
        """
        incomplete_graph = {
            "nodes": [],
            "edges": [],
            # 'meta' key intentionally missing
        }

        with patch("backend.app.services.decision_engine.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            engine = DecisionEngine(api_key="fake-api-key-for-testing")

            with pytest.raises(ValueError, match="missing required keys"):
                engine.analyze_fault_graph(graph_payload=incomplete_graph)

            # The LLM must NOT have been called — we fail fast before it.
            mock_client.models.generate_content.assert_not_called()

    def test_empty_api_key_raises_value_error_on_init(self) -> None:
        """
        GIVEN  an empty api_key string
        WHEN   DecisionEngine is instantiated
        THEN   ValueError is raised immediately.

        This prevents silent unauthenticated Gemini requests that would
        always 401 and waste quota.  Fail Fast — 01_architecture.md §5.
        """
        with patch("backend.app.services.decision_engine.genai"):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                DecisionEngine(api_key="")


# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — ARCHITECTURAL JUSTIFICATION (as a documented test module constant)
# ══════════════════════════════════════════════════════════════════════════════

ARCHITECTURAL_JUSTIFICATION: str = """
Task 3: Why deterministic mocking of external boundaries is mandatory in CI.

In a Continuous Integration pipeline, every test must be hermetic — meaning
its outcome depends solely on the correctness of the local code, not on the
availability, latency, or quota state of a third-party service like Kafka or
the Gemini API.  Without mocking, a transient network blip, an exhausted free-
tier quota, or a broker restart would cause the CI build to fail even when the
application code is perfectly correct, making the pipeline unreliable as a
quality gate and eroding developer trust in the test suite over time.

At Staff-level engineering, deterministic mocking is also a design forcing
function: if a component cannot be tested without a live external service, it
signals that the component has violated the Single Responsibility Principle
and mixed infrastructure concerns with business logic — exactly the architectural
smell that the Modular Monolith boundaries in 01_architecture.md are designed
to prevent.
"""
