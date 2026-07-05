"""
Graph Analyzer Service
======================
The core algorithmic layer of the Analysis domain. Responsible for ingesting
validated distributed trace events and constructing a directed dependency graph
that can be queried for root-cause analysis.

DOMAIN RESPONSIBILITY (from 01_architecture.md §2):
    This service lives in ``backend/app/services/`` and belongs to the
    **Analysis** domain. Its sole job is data transformation: convert a list
    of ``TraceEvent`` records into a queryable ``nx.DiGraph``, then export
    that graph as a frontend-ready JSON payload.

    It does NOT:
    - Perform HTTP calls (no ``requests.get()`` / ``httpx``).
    - Hold application state across requests (stateless service pattern).
    - Contain AI/ML inference logic (that belongs in the Agent domain).

WHY NETWORKX DiGraph (and not a plain dict)?
    A directed graph (DiGraph) precisely models inter-service calls: the
    direction of an edge encodes the *caller → callee* relationship, which
    is the key primitive for root-cause analysis. If User-DB fails and we
    want to find all affected upstream services, we traverse the graph in
    reverse (predecessors), not by scanning logs linearly.

TIME COMPLEXITY JUSTIFICATION:
    - Graph construction: O(V + E) — each node and edge is visited exactly once.
    - Root-cause traversal (e.g., nx.ancestors): O(V + E) using BFS/DFS.
    - Linear log scanning alternative: O(N²) in the worst case (N = log lines),
      since every log must be compared against every other to identify patterns.
    For a system with 100 services and 300 trace hops, graph traversal runs in
    constant proportional time regardless of total log volume.

DESIGN PATTERN — Stateless Service:
    ``GraphAnalyzer`` is instantiated fresh per request (or per batch) rather
    than maintained as a singleton. This makes it trivially testable, avoids
    stale state bugs, and allows future phases to switch to an incremental
    update pattern without breaking the existing API surface.

REFERENCES:
    - 01_architecture.md §2 (Directory & Domain Rules)
    - 01_architecture.md §3 (End-to-End Data Flow, step 3: Topology Mapping)
    - 01_architecture.md §5 (Architectural Guardrails: Explainability)
    - 98_project_constraints.md (NetworkX is an approved dependency)
    - 99_ai_rules.md (Strict typing, Pydantic v2, interview-quality comments)
"""

import json
import logging
from typing import Any

import networkx as nx

from backend.contracts.events.trace import TraceEvent, TraceStatus

# ── Module logger ──────────────────────────────────────────────────────────────
# Inherits the structured-JSON handler configured in main.py's lifespan,
# so every log line from this module appears in the same machine-parseable
# format as all other backend components.
logger: logging.Logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMA (Pydantic models for the frontend-facing JSON payload)
# ══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, ConfigDict


class GraphNode(BaseModel):
    """
    Represents a single service node in the frontend topology graph.

    Attributes:
        id:             Logical service name (e.g., "API-Gateway").
        status:         Worst-case health status observed for this node across
                        all trace hops in the current analysis window.
        error_metadata: The structured error detail from the first failure
                        logged against this node; None if healthy.
        call_count:     Total number of incoming trace hops targeting this node.
        failure_count:  Number of those hops that resulted in a failure.
    """

    model_config = ConfigDict(strict=False)

    id: str
    status: str  # "success" | "failed" | "degraded"
    error_metadata: dict[str, Any] | None = None
    call_count: int = 0
    failure_count: int = 0


class GraphEdge(BaseModel):
    """
    Represents a directed inter-service call edge in the frontend topology graph.

    Attributes:
        source: The calling service (graph edge origin).
        target: The receiving service (graph edge destination).
        weight: How many trace hops traversed this specific edge.
                A high weight on an edge leading to a failed node is a
                strong signal of a critical dependency path.
    """

    model_config = ConfigDict(strict=False)

    source: str
    target: str
    weight: int = 1


class GraphPayload(BaseModel):
    """
    The complete, frontend-ready JSON payload exported by ``GraphAnalyzer``.

    Schema (matches the required contract from the Phase 6 spec):
    {
        "nodes": [{"id": "...", "status": "...", "error_metadata": {...}}],
        "edges": [{"source": "...", "target": "..."}]
    }

    The ``meta`` field provides summary statistics for the frontend dashboard
    (e.g., total failures, root cause candidate) without requiring the frontend
    to perform its own graph traversal.
    """

    model_config = ConfigDict(strict=False)

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: dict[str, Any] = {}


# ══════════════════════════════════════════════════════════════════════════════
# CORE SERVICE CLASS
# ══════════════════════════════════════════════════════════════════════════════


class GraphAnalyzer:
    """
    Stateless service that transforms a batch of ``TraceEvent`` records into a
    queryable ``nx.DiGraph`` and exports the result as a ``GraphPayload``.

    USAGE (per-request pattern):
        analyzer = GraphAnalyzer()
        analyzer.build_graph(validated_trace_events)
        payload = analyzer.export_payload()

    THREAD SAFETY:
        Each instance maintains its own ``nx.DiGraph``. Do not share instances
        across concurrent requests. In FastAPI, instantiate inside the route
        handler or inject via a factory dependency — never as a module-level singleton.

    INTERVIEW WHITEBOARD SUMMARY:
        Input  → List[TraceEvent]   (validated Pydantic models)
        Step 1 → Build nx.DiGraph   O(V + E)
        Step 2 → Annotate nodes     O(V)
        Step 3 → Find root cause    O(V + E)  [BFS via nx.ancestors]
        Output → GraphPayload JSON  O(V + E)
    """

    def __init__(self) -> None:
        """
        Initialise a fresh directed graph.

        WHY DiGraph (not Graph):
            nx.DiGraph enforces edge directionality, which is essential here.
            The edge (API-Gateway → Auth-Service) means "Gateway depends on Auth";
            reversing it would mean the opposite. Undirected graphs lose this
            crucial caller/callee semantics.
        """
        # The core data structure: every service = node, every call = edge.
        self._graph: nx.DiGraph = nx.DiGraph()

        logger.debug("GraphAnalyzer initialised with empty DiGraph")

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def build_graph(self, events: list[TraceEvent]) -> None:
        """
        Ingest a list of ``TraceEvent`` records and populate the internal graph.

        ALGORITHM (O(V + E)):
            For each event (one directed edge):
            1. Upsert ``source_node``  — add if absent, leave untouched if present.
            2. Upsert ``target_node``  — same.
            3. Add or increment the directed edge (source → target).
            4. If status is FAILED or DEGRADED, promote the target node's health
               status (never downgrade: failed > degraded > success).
            5. Attach the first ``error_metadata`` payload seen for a failing node.

        WHY "upsert" rather than always overwrite:
            A node like "Auth-Service" may appear in dozens of trace hops.
            We never want a healthy hop to retroactively clear a failure flag
            set by a prior hop in the same analysis window.

        Args:
            events: A list of validated ``TraceEvent`` Pydantic model instances.
                    Passed in from the REST router or Kafka consumer.

        Raises:
            ValueError: If ``events`` is empty (prevents returning a meaningless
                        empty graph that would silently appear correct to the caller).
        """
        if not events:
            raise ValueError(
                "GraphAnalyzer.build_graph() received an empty event list. "
                "Provide at least one TraceEvent to build a meaningful graph."
            )

        logger.info(
            "Building dependency graph — processing %d trace events", len(events)
        )

        for event in events:
            # ── Step 1: Upsert source node ─────────────────────────────────
            # If the source node is new, initialise it with a healthy baseline.
            # If it already exists (seen in a prior event), leave its attributes
            # untouched — we never downgrade an existing failure to healthy.
            if not self._graph.has_node(event.source_node):
                self._graph.add_node(
                    event.source_node,
                    status=TraceStatus.SUCCESS.value,
                    error_metadata=None,
                    call_count=0,
                    failure_count=0,
                )

            # ── Step 2: Upsert target node ─────────────────────────────────
            if not self._graph.has_node(event.target_node):
                self._graph.add_node(
                    event.target_node,
                    status=TraceStatus.SUCCESS.value,
                    error_metadata=None,
                    call_count=0,
                    failure_count=0,
                )

            # ── Step 3: Add or weight the directed edge ────────────────────
            # ``weight`` counts how many trace hops traversed this exact edge.
            # A high-weight edge pointing to a failed node is the critical path.
            if self._graph.has_edge(event.source_node, event.target_node):
                self._graph[event.source_node][event.target_node]["weight"] += 1
            else:
                self._graph.add_edge(event.source_node, event.target_node, weight=1)

            # ── Step 4: Update target node's call counter ──────────────────
            self._graph.nodes[event.target_node]["call_count"] += 1

            # ── Step 5: Annotate node with failure state ───────────────────
            # Health status is monotonically increasing: success → degraded → failed.
            # A node that has been marked "failed" is never reverted to "degraded"
            # or "success" by a later healthy hop in the same batch.
            if event.status in (TraceStatus.FAILED, TraceStatus.DEGRADED):
                self._graph.nodes[event.target_node]["failure_count"] += 1

                # Only promote the status; never demote (failed > degraded > success).
                current_status = self._graph.nodes[event.target_node]["status"]
                new_status = event.status.value

                if self._should_promote_status(current_status, new_status):
                    self._graph.nodes[event.target_node]["status"] = new_status
                    logger.debug(
                        "Node status promoted — node=%s old=%s new=%s",
                        event.target_node,
                        current_status,
                        new_status,
                    )

                # Attach error metadata only from the *first* failure observed
                # for this node, preserving the original root error signal.
                if (
                    self._graph.nodes[event.target_node]["error_metadata"] is None
                    and event.error_metadata is not None
                ):
                    self._graph.nodes[event.target_node]["error_metadata"] = (
                        event.error_metadata.model_dump()
                    )

        logger.info(
            "Graph built — nodes=%d edges=%d",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    def export_payload(self) -> GraphPayload:
        """
        Serialise the internal ``nx.DiGraph`` into a ``GraphPayload`` for the API.

        This method is a pure transformation: it reads graph state and maps it
        to Pydantic models that FastAPI will serialise to JSON. No mutation of
        the graph occurs here.

        Returns:
            ``GraphPayload`` — the complete, frontend-ready topology payload
            including nodes, edges, and derived summary metadata.

        Raises:
            RuntimeError: If called before ``build_graph()`` (empty graph guard).
        """
        if self._graph.number_of_nodes() == 0:
            raise RuntimeError(
                "GraphAnalyzer.export_payload() called on an empty graph. "
                "Call build_graph() with at least one TraceEvent first."
            )

        # ── Serialise nodes ────────────────────────────────────────────────
        nodes: list[GraphNode] = [
            GraphNode(
                id=node_id,
                status=data.get("status", TraceStatus.SUCCESS.value),
                error_metadata=data.get("error_metadata"),
                call_count=data.get("call_count", 0),
                failure_count=data.get("failure_count", 0),
            )
            for node_id, data in self._graph.nodes(data=True)
        ]

        # ── Serialise edges ────────────────────────────────────────────────
        edges: list[GraphEdge] = [
            GraphEdge(
                source=source,
                target=target,
                weight=data.get("weight", 1),
            )
            for source, target, data in self._graph.edges(data=True)
        ]

        # ── Derive summary metadata for the dashboard ──────────────────────
        # ``nx.ancestors(G, node)`` returns all nodes that have a directed path
        # to ``node`` — i.e., all services that depend (directly or indirectly)
        # on a failed node. This is the key graph traversal for blast-radius analysis.
        meta: dict[str, Any] = self._compute_meta()

        return GraphPayload(nodes=nodes, edges=edges, meta=meta)

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _should_promote_status(current: str, incoming: str) -> bool:
        """
        Determine whether ``incoming`` status is a promotion over ``current``.

        The health severity order is: success (0) < degraded (1) < failed (2).
        A node's status should only ever increase in severity within one analysis
        window, never decrease — a "failed" node is never reset to "degraded"
        by a later degraded hop.

        Args:
            current:  The node's currently stored status string.
            incoming: The status from the latest trace event for this node.

        Returns:
            ``True`` if ``incoming`` is more severe than ``current``.
        """
        # Severity ordering: lower index = lower severity.
        _SEVERITY: dict[str, int] = {
            TraceStatus.SUCCESS.value: 0,
            TraceStatus.DEGRADED.value: 1,
            TraceStatus.FAILED.value: 2,
        }
        return _SEVERITY.get(incoming, 0) > _SEVERITY.get(current, 0)

    def _compute_meta(self) -> dict[str, Any]:
        """
        Derive summary statistics from the current graph state.

        ALGORITHM:
            1. Identify all failed nodes (O(V)).
            2. For the primary failure (lowest in-call-count = likely root cause),
               compute its ``nx.ancestors`` — all nodes that depend on it (O(V+E)).
            3. Return counts and the root cause candidate name for the dashboard.

        WHY ancestors (not descendants)?
            In a caller→callee DiGraph, ``nx.ancestors(G, failed_node)`` returns
            all nodes that have a directed path *to* ``failed_node``, meaning
            they called it (directly or through intermediaries). These are the
            services whose upstream requests are now failing because of this node.
            This is the "blast radius" — the set of impacted services.

        Returns:
            A dict with total_nodes, total_edges, failed_node_count, and
            root_cause_candidate (the failed node with the fewest predecessors,
            i.e., least upstream callers — the most "leaf" failed node).
        """
        total_failed = sum(
            1
            for _, data in self._graph.nodes(data=True)
            if data.get("status") == TraceStatus.FAILED.value
        )

        # The root cause heuristic: the failed node with the fewest in-degree
        # (fewest callers in this trace) is most likely the originating failure.
        # A DB with in-degree 1 is a stronger root cause candidate than an
        # API-Gateway with in-degree 10 (it's called by many, so unlikely to be root).
        root_cause_candidate: str | None = None
        failed_nodes = [
            (node_id, self._graph.in_degree(node_id))
            for node_id, data in self._graph.nodes(data=True)
            if data.get("status") == TraceStatus.FAILED.value
        ]
        if failed_nodes:
            # Pick the failed node with the smallest in-degree as the root cause.
            root_cause_candidate = min(failed_nodes, key=lambda x: x[1])[0]

        # Compute the blast radius: all ancestors of the root cause candidate.
        blast_radius: list[str] = []
        if root_cause_candidate:
            blast_radius = list(nx.ancestors(self._graph, root_cause_candidate))

        logger.info(
            "Graph meta computed — failed_nodes=%d root_cause=%s blast_radius=%s",
            total_failed,
            root_cause_candidate,
            blast_radius,
        )

        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "failed_node_count": total_failed,
            "root_cause_candidate": root_cause_candidate,
            "blast_radius": blast_radius,
        }


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION (for router injection)
# ══════════════════════════════════════════════════════════════════════════════


def analyze_traces(events: list[TraceEvent]) -> GraphPayload:
    """
    Convenience function: instantiate, build, and export in one call.

    This is the primary entry point called by the FastAPI router and the
    Kafka consumer's processing pipeline. It encapsulates the three-step
    lifecycle so callers never need to manage ``GraphAnalyzer`` instances directly.

    Args:
        events: A validated list of ``TraceEvent`` Pydantic model instances.

    Returns:
        A ``GraphPayload`` ready for JSON serialisation by FastAPI's response model.

    Example (in a FastAPI router):
        @router.post("/analyze")
        async def analyze(events: list[TraceEvent]) -> GraphPayload:
            return analyze_traces(events)
    """
    analyzer = GraphAnalyzer()
    analyzer.build_graph(events)
    return analyzer.export_payload()


# ══════════════════════════════════════════════════════════════════════════════
# TEST HARNESS — Run directly to verify schema output
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Self-contained test harness for immediate console verification.

    Scenario: Cascading microservice failure.
        Client → API-Gateway (OK)
        API-Gateway → Auth-Service (OK)
        Auth-Service → User-DB (FAILED — DB_TIMEOUT_ERROR)
        API-Gateway → Auth-Service (FAILED — 500 cascaded from User-DB timeout)
        API-Gateway → Notification-Service (DEGRADED — slow response, SLO breach)

    This represents a realistic cascade: User-DB fails → Auth-Service propagates
    the error → API-Gateway sees the 500 and logs a second failure.
    Expected root cause candidate: "User-DB" (in-degree 1, sole failed leaf).
    Expected blast radius: ["Auth-Service", "API-Gateway"] (dependents of User-DB).
    """
    from datetime import datetime, timezone

    print("\n" + "=" * 72)
    print("  ARF Phase 6 -- GraphAnalyzer Test Harness")
    print("  Scenario: Cascading Failure (Client -> Gateway -> Auth -> DB)")
    print("=" * 72 + "\n")

    # ── Mock trace event payloads ──────────────────────────────────────────
    # In production these arrive as validated Pydantic models from the REST
    # router or the Kafka consumer. Here we construct them directly.
    mock_events: list[TraceEvent] = [
        # Hop 1: Client → API-Gateway (healthy)
        TraceEvent(
            trace_id="req-9912",
            timestamp=datetime(2026, 7, 5, 12, 0, 1, tzinfo=timezone.utc),
            source_node="Client",
            target_node="API-Gateway",
            status=TraceStatus.SUCCESS,
        ),
        # Hop 2: API-Gateway → Auth-Service (initially healthy)
        TraceEvent(
            trace_id="req-9912",
            timestamp=datetime(2026, 7, 5, 12, 0, 2, tzinfo=timezone.utc),
            source_node="API-Gateway",
            target_node="Auth-Service",
            status=TraceStatus.SUCCESS,
        ),
        # Hop 3: Auth-Service → User-DB (ROOT CAUSE — DB timeout)
        TraceEvent(
            trace_id="req-9912",
            timestamp=datetime(2026, 7, 5, 12, 0, 3, tzinfo=timezone.utc),
            source_node="Auth-Service",
            target_node="User-DB",
            status=TraceStatus.FAILED,
            error_metadata={  # type: ignore[arg-type]
                # Pydantic will coerce this dict into ErrorMetadata
                "error_code": "DB_TIMEOUT_ERROR",
                "message": "Connection timeout while querying User-DB replica",
                "latency_ms": 30042.7,
                "extra": {"db_host": "user-db-primary:5432", "retry_count": 3},
            },
        ),
        # Hop 4: API-Gateway → Auth-Service (FAILED — cascaded from User-DB)
        TraceEvent(
            trace_id="req-9912",
            timestamp=datetime(2026, 7, 5, 12, 0, 4, tzinfo=timezone.utc),
            source_node="API-Gateway",
            target_node="Auth-Service",
            status=TraceStatus.FAILED,
            error_metadata={  # type: ignore[arg-type]
                "error_code": "500_INTERNAL_SERVER_ERROR",
                "message": "Dependency 'User-DB' failed to respond within SLO",
                "latency_ms": 30100.2,
                "extra": {"upstream_error": "DB_TIMEOUT_ERROR"},
            },
        ),
        # Hop 5: API-Gateway → Notification-Service (DEGRADED — SLO breach)
        TraceEvent(
            trace_id="req-9912",
            timestamp=datetime(2026, 7, 5, 12, 0, 5, tzinfo=timezone.utc),
            source_node="API-Gateway",
            target_node="Notification-Service",
            status=TraceStatus.DEGRADED,
            error_metadata={  # type: ignore[arg-type]
                "error_code": "HIGH_LATENCY_WARNING",
                "message": "Response latency 4200ms exceeds 1000ms SLO threshold",
                "latency_ms": 4200.0,
                "extra": {},
            },
        ),
    ]

    # ── Run the analyzer ───────────────────────────────────────────────────
    try:
        payload: GraphPayload = analyze_traces(mock_events)
    except (ValueError, RuntimeError) as exc:
        print(f"[ERROR] GraphAnalyzer raised: {exc}")
        raise SystemExit(1) from exc

    # ── Print JSON output for immediate schema verification ────────────────
    output_dict = payload.model_dump()
    print("OUTPUT JSON PAYLOAD:")
    print("-" * 72)
    print(json.dumps(output_dict, indent=2, default=str))
    print("-" * 72)

    # ── Human-readable summary ─────────────────────────────────────────────
    print("\nANALYSIS SUMMARY:")
    meta = output_dict["meta"]
    print(f"  Total Nodes         : {meta['total_nodes']}")
    print(f"  Total Edges         : {meta['total_edges']}")
    print(f"  Failed Node Count   : {meta['failed_node_count']}")
    print(f"  Root Cause Candidate: {meta['root_cause_candidate']}")
    print(f"  Blast Radius        : {meta['blast_radius']}")
    print("\n" + "=" * 72)
    print("  [OK] Schema verification complete. Ready for Phase 6 router integration.")
    print("=" * 72 + "\n")
