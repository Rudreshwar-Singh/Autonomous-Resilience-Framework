"""
Trace Event Contract
====================
Defines the canonical Pydantic v2 schema for a distributed trace event — a
single "hop" in an inter-service call chain (e.g., API-Gateway → Auth-Service).

WHY A SEPARATE CONTRACT (NOT REUSING TelemetryEvent):
    ``TelemetryEvent`` is a flat, service-level log (one event per service).
    ``TraceEvent`` is a *relational* record: it captures the directed relationship
    between two nodes (source → target) in a single call hop, which is the
    primitive data unit needed to construct a NetworkX dependency graph.

    Merging the two would violate the Single Responsibility Principle and force
    the graph builder to guess which service is the "source" and which is the
    "target" from unstructured log text — a fragile anti-pattern.

DATA FLOW:
    1. Mock fault scenarios (``data/fault_scenarios/``) produce ``TraceEvent`` records.
    2. The REST telemetry router or future Kafka consumer receives and validates them.
    3. The validated ``TraceEvent`` list is forwarded to ``GraphAnalyzer.build_graph()``.
    4. The resulting graph JSON is served to the frontend via the /api/v1/graph router.

STRICT VALIDATION:
    All boundary inputs (API, Kafka, mock scripts) MUST be validated through
    this model before reaching the Analysis domain. This is the project's
    "Fail Fast" guardrail (see 01_architecture.md §5).
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class TraceStatus(str, Enum):
    """
    Allowed health outcomes for a single inter-service hop.

    ``SUCCESS`` — the call completed without errors.
    ``FAILED``  — the call failed (network error, timeout, 5xx response, etc.).
    ``DEGRADED``— the call succeeded but exceeded SLO thresholds (high latency).

    Using an Enum over a plain str field ensures the graph builder never
    receives an unexpected status string that would silently mis-classify a node.
    """

    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"


class ErrorMetadata(BaseModel):
    """
    Structured metadata attached to a failed or degraded hop.

    Keeping error details in a nested Pydantic model (not a free-form dict)
    enforces a consistent shape that the Analysis domain and the LLM Agent
    can reliably parse without defensive ``dict.get()`` chains.
    """

    model_config = ConfigDict(strict=False)

    error_code: str = Field(
        description="Machine-readable error code (e.g. 'DB_TIMEOUT', '500_INTERNAL_SERVER_ERROR').",
        examples=["DB_TIMEOUT_ERROR", "500_INTERNAL_SERVER_ERROR"],
    )
    message: str = Field(
        min_length=1,
        max_length=1024,
        description="Human-readable explanation of the failure.",
        examples=["Connection timeout while querying User-DB"],
    )
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds for this hop, if measurable.",
        examples=[4320.5],
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional metadata for extensibility (e.g., HTTP status code).",
    )


class TraceEvent(BaseModel):
    """
    Immutable, validated representation of a single distributed trace hop.

    A ``TraceEvent`` encodes ONE directed edge in the service dependency graph:
    ``source_node`` called ``target_node`` and the result was ``status``.
    Aggregating a list of ``TraceEvent`` records constructs the full call graph.

    This model is imported by:
        - ``backend/app/routers/telemetry.py``     (REST ingestion endpoint)
        - ``backend/app/services/graph_analyzer.py`` (graph construction)
        - ``backend/app/routers/graph.py``          (topology query endpoints)
        - Future: ``backend/telemetry/consumer.py`` (Kafka consumer validation)

    Attributes:
        trace_id:     Unique identifier linking all hops in one logical request.
        event_id:     UUID uniquely identifying *this specific hop* for dedup.
        timestamp:    UTC datetime of the call origination (not receipt).
        source_node:  Logical name of the calling service (graph edge source).
        target_node:  Logical name of the receiving service (graph edge target).
        status:       Outcome of this hop (``success`` / ``failed`` / ``degraded``).
        error_metadata: Structured failure detail; populated only when status != success.
    """

    model_config = ConfigDict(strict=False)

    trace_id: str = Field(
        description="Logical trace ID grouping all hops in one end-to-end request.",
        examples=["req-9912", "trace-abc-001"],
    )
    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for this hop; auto-generated if omitted.",
    )
    timestamp: datetime = Field(
        description="UTC datetime when this inter-service call was initiated.",
        examples=["2026-07-05T12:00:01Z"],
    )
    source_node: str = Field(
        min_length=1,
        max_length=128,
        description="Logical name of the service making the call.",
        examples=["API-Gateway", "Auth-Service"],
    )
    target_node: str = Field(
        min_length=1,
        max_length=128,
        description="Logical name of the service receiving the call.",
        examples=["Auth-Service", "User-DB"],
    )
    status: TraceStatus = Field(
        description="Outcome of this call hop.",
        examples=["success", "failed"],
    )
    error_metadata: ErrorMetadata | None = Field(
        default=None,
        description="Structured failure details; None if status is 'success'.",
    )
