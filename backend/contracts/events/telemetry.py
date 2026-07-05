"""
Telemetry Event Contract
========================
Defines the canonical Pydantic v2 schema for a telemetry event as it travels
through the system: ingested via REST → serialised to Kafka → consumed and
validated → forwarded to the Analysis domain.

WHY A SHARED CONTRACT MODULE:
    All producers (REST router, future OpenTelemetry agents) and all consumers
    (Kafka worker, Analysis domain) import *this single model*.  Changing the
    schema here is the one place where breaking changes are caught by static
    analysis (mypy) and at Pydantic validation boundaries — not buried in
    scattered dict literals.

STRICT VALIDATION:
    model_config = ConfigDict(strict=True) means Pydantic will NOT silently
    coerce types (e.g., int → str). Every field must arrive with the exact
    Python type declared, making hidden data-quality issues loud and early.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class LogLevel(str, Enum):
    """
    Allowed severity levels for a telemetry event.

    Mirrors the RFC 5424 syslog severity subset that is relevant to the
    Autonomous Resilience Framework's alerting rules.  Using an Enum instead
    of a plain str field means the API and Kafka consumer reject unknown
    levels at parse time, not at alerting time.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TelemetryEvent(BaseModel):
    """
    Immutable, validated representation of a single telemetry event.

    This model is the *only* authoritative definition of the event schema.
    It is imported by:
        - backend/app/routers/telemetry.py  (REST ingestion)
        - backend/app/services/kafka_producer.py  (serialisation to Kafka)
        - backend/telemetry/consumer.py  (deserialisation & validation)
        - backend/analysis/  (future graph-correlation logic)

    Attributes:
        event_id:     Auto-generated UUID v4 uniquely identifying this event.
                      Consumers use this for idempotent deduplication.
        timestamp:    UTC datetime of event origination (not ingestion).
                      Stored as a timezone-aware datetime to prevent DST bugs.
        service_name: Logical name of the emitting service (e.g. "payment-svc").
                      Used by the dependency graph to locate the node responsible.
        level:        RFC 5424-derived severity level (see LogLevel enum).
        message:      Human-readable event description.  Must be non-empty;
                      max 2048 chars to prevent log-injection DoS.
    """

    model_config = ConfigDict(strict=False)

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event; auto-generated if omitted.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    timestamp: datetime = Field(
        description="UTC datetime when the event originated in the source service.",
        examples=["2026-07-04T18:30:00+00:00"],
    )
    service_name: str = Field(
        min_length=1,
        max_length=128,
        description="Logical name of the service that emitted this event.",
        examples=["payment-svc", "auth-gateway", "inventory-api"],
    )
    level: LogLevel = Field(
        description="Severity level of the event (DEBUG / INFO / WARNING / ERROR / CRITICAL).",
        examples=["ERROR"],
    )
    message: str = Field(
        min_length=1,
        max_length=2048,
        description="Human-readable description of the event.",
        examples=["Database connection pool exhausted — retrying in 5 s"],
    )
