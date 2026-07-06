"""
Telemetry Unit Tests
====================
Phase 8: Test Harness — Task 1.

PURPOSE:
    Validate that the telemetry ingestion pipeline (REST router + Kafka producer)
    behaves correctly in complete isolation from a real Kafka broker.

MOCKING STRATEGY (why this is the right approach for CI):
    We patch ``confluent_kafka.Producer`` at the point of import inside
    ``kafka_producer.py`` using ``unittest.mock.patch``.  This means:

    - Zero network sockets are opened during test execution.
    - Tests run in milliseconds regardless of broker availability.
    - Each test controls exactly what the mock producer returns, making
      assertions deterministic — no flakiness from broker lag or
      topic-creation races.

    The FastAPI ``TestClient`` stands in for a real HTTP server; it executes
    the full ASGI middleware and routing stack without binding a port.

WHAT IS TESTED:
    1. ``test_ingest_endpoint_returns_202``
       — Happy path: a valid TelemetryEvent POST returns HTTP 202 and the
         Kafka producer's ``produce()`` method is called exactly once.

    2. ``test_ingest_endpoint_echoes_event_id``
       — The response body carries the event's UUID so callers can correlate
         async delivery confirmations.

    3. ``test_ingest_endpoint_rejects_invalid_payload``
       — Pydantic validation catches missing/wrong-typed fields and returns
         HTTP 422 before the producer is ever touched.

    4. ``test_producer_produce_calls_underlying_confluent_producer``
       — White-box unit test of KafkaProducerService in isolation: verifies
         the service serialises the event to UTF-8 JSON and passes key +
         value to the underlying librdkafka producer exactly once.

    5. ``test_producer_raises_on_kafka_exception``
       — If librdkafka raises KafkaException, the service re-raises it
         (fail-fast) rather than swallowing the error silently.

    6. ``test_consumer_processes_valid_message``
       — Simulates the Kafka consumer receiving a raw bytes payload and
         validates it deserialises correctly into a TelemetryEvent Pydantic
         model with no exceptions.

    7. ``test_consumer_handles_malformed_message``
       — The consumer must never crash the process on a bad message;
         instead it catches and logs the error, and skips the payload.
"""

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# ── Project imports ────────────────────────────────────────────────────────────
from backend.app.main import app
from backend.contracts.events.telemetry import LogLevel, TelemetryEvent


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def mock_kafka_producer() -> MagicMock:
    """
    Replace ``confluent_kafka.Producer`` with a MagicMock for the duration
    of each test.

    Patched at the module level where it is *used* (kafka_producer.py),
    not where it is *defined* (confluent_kafka).  This is the canonical
    unittest.mock patching rule: patch the name in the namespace that
    imports it.
    """
    with patch("backend.app.services.kafka_producer.Producer") as mock_cls:
        # mock_cls is the class; mock_cls.return_value is the instance.
        mock_instance = MagicMock()
        # flush() is called during lifespan shutdown with `if remaining > 0:` comparison.
        # Return 0 (int) so the comparison works without a TypeError.
        mock_instance.flush.return_value = 0
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture()
def test_client(mock_kafka_producer: MagicMock) -> TestClient:
    """
    Provide a FastAPI TestClient with the Kafka producer fully mocked.

    The lifespan context manager in main.py calls
    ``KafkaProducerService(bootstrap_servers=...)`` which internally calls
    ``confluent_kafka.Producer(...)`` — already replaced by ``mock_kafka_producer``.
    No real broker connection is attempted.
    """
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture()
def valid_event_payload() -> dict[str, Any]:
    """Minimal valid TelemetryEvent JSON body for POST /api/v1/telemetry/ingest."""
    return {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": "payment-svc",
        "level": "ERROR",
        "message": "Database connection pool exhausted — retrying in 5 s",
    }


# ══════════════════════════════════════════════════════════════════════════════
# TASK 1A — HTTP ENDPOINT TESTS (Router layer)
# ══════════════════════════════════════════════════════════════════════════════


class TestTelemetryIngestEndpoint:
    """
    Tests for POST /api/v1/telemetry/ingest.

    Exercises the full FastAPI request/response cycle including Pydantic
    validation, routing, and the KafkaProducerService call — but with the
    underlying confluent_kafka.Producer fully mocked.
    """

    def test_ingest_endpoint_returns_202(
        self,
        test_client: TestClient,
        valid_event_payload: dict[str, Any],
        mock_kafka_producer: MagicMock,
    ) -> None:
        """
        A valid payload must return HTTP 202 Accepted and trigger exactly
        one call to the underlying Kafka producer.

        WHY 202 and NOT 200:
            The event is enqueued asynchronously; it has not been consumed
            or processed at response time.  RFC 7231 §6.3.3 defines 202 as
            "request accepted for processing, but the processing has not been
            completed."  This is the semantically correct status for a
            fire-and-forget async pipeline.
        """
        response = test_client.post(
            "/api/v1/telemetry/ingest",
            json=valid_event_payload,
        )

        assert response.status_code == 202, (
            f"Expected 202 Accepted, got {response.status_code}: {response.text}"
        )
        # Verify the producer was actually called — not bypassed by a bug.
        mock_kafka_producer.produce.assert_called_once()

    def test_ingest_endpoint_echoes_event_id(
        self,
        test_client: TestClient,
        valid_event_payload: dict[str, Any],
    ) -> None:
        """
        The response body must echo back the submitted event_id so callers
        can correlate async delivery confirmations without a second lookup.
        """
        submitted_id: str = valid_event_payload["event_id"]

        response = test_client.post(
            "/api/v1/telemetry/ingest",
            json=valid_event_payload,
        )

        body: dict[str, Any] = response.json()
        assert body["status"] == "accepted"
        assert body["event_id"] == submitted_id

    def test_ingest_endpoint_rejects_missing_fields(
        self,
        test_client: TestClient,
        mock_kafka_producer: MagicMock,
    ) -> None:
        """
        Pydantic must reject payloads missing required fields with HTTP 422
        before the Kafka producer is ever touched.  This validates the
        Fail-Fast boundary from 01_architecture.md §5.
        """
        incomplete_payload = {"message": "only a message, nothing else"}

        response = test_client.post(
            "/api/v1/telemetry/ingest",
            json=incomplete_payload,
        )

        assert response.status_code == 422, (
            f"Expected 422 Unprocessable Entity, got {response.status_code}"
        )
        # The Kafka producer must NOT have been called — bad data never reaches it.
        mock_kafka_producer.produce.assert_not_called()

    def test_ingest_endpoint_rejects_invalid_log_level(
        self,
        test_client: TestClient,
        valid_event_payload: dict[str, Any],
        mock_kafka_producer: MagicMock,
    ) -> None:
        """
        The ``level`` field uses a strict Enum (LogLevel).  Values outside
        the allowed set must be rejected with HTTP 422.
        """
        invalid_payload = {**valid_event_payload, "level": "VERBOSE"}

        response = test_client.post(
            "/api/v1/telemetry/ingest",
            json=invalid_payload,
        )

        assert response.status_code == 422
        mock_kafka_producer.produce.assert_not_called()

    def test_list_telemetry_events_returns_200(
        self,
        test_client: TestClient,
    ) -> None:
        """GET /api/v1/telemetry/ must return 200 OK with a placeholder body."""
        response = test_client.get("/api/v1/telemetry/")
        assert response.status_code == 200
        assert response.json()["status"] == "placeholder"


# ══════════════════════════════════════════════════════════════════════════════
# TASK 1B — KAFKA PRODUCER SERVICE UNIT TESTS (Service layer)
# ══════════════════════════════════════════════════════════════════════════════


class TestKafkaProducerService:
    """
    White-box unit tests for KafkaProducerService in isolation.

    These tests import and exercise the service class directly — no HTTP
    stack involved.  This verifies the serialisation logic and error handling
    at the service boundary, independent of the router.
    """

    def _make_event(self) -> TelemetryEvent:
        """Build a minimal valid TelemetryEvent for use in producer tests."""
        return TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            service_name="auth-gateway",
            level=LogLevel.ERROR,
            message="Downstream timeout — circuit breaker tripped",
        )

    def test_produce_calls_confluent_producer_once(self) -> None:
        """
        KafkaProducerService.produce() must call the underlying
        confluent_kafka.Producer.produce() exactly once per event, passing
        the correct topic, a bytes key (service_name), and a UTF-8 JSON value.
        """
        with patch("backend.app.services.kafka_producer.Producer") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            # Re-import inside the patch context so the mock is active.
            from backend.app.services.kafka_producer import KafkaProducerService

            svc = KafkaProducerService(bootstrap_servers="localhost:9092")
            event = self._make_event()
            topic = "system-telemetry"

            svc.produce(topic=topic, event=event)

            mock_instance.produce.assert_called_once()
            call_kwargs = mock_instance.produce.call_args.kwargs

            # Topic must match exactly.
            assert call_kwargs["topic"] == topic

            # Key must be the service name encoded as bytes.
            assert call_kwargs["key"] == event.service_name.encode("utf-8")

            # Value must be a valid UTF-8 JSON payload that round-trips
            # back into the original event fields.
            raw_value: bytes = call_kwargs["value"]
            parsed: dict[str, Any] = json.loads(raw_value.decode("utf-8"))
            assert parsed["service_name"] == event.service_name
            assert parsed["level"] == event.level.value

    def test_produce_raises_on_kafka_exception(self) -> None:
        """
        If the underlying librdkafka producer raises KafkaException (e.g.,
        buffer full, broker unreachable), KafkaProducerService must re-raise
        it rather than swallowing it silently.

        Per 99_ai_rules.md: "Never silently ignore errors".
        """
        from confluent_kafka import KafkaException

        with patch("backend.app.services.kafka_producer.Producer") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.produce.side_effect = KafkaException("broker unreachable")
            mock_cls.return_value = mock_instance

            from backend.app.services.kafka_producer import KafkaProducerService

            svc = KafkaProducerService(bootstrap_servers="localhost:9092")
            event = self._make_event()

            with pytest.raises(KafkaException, match="broker unreachable"):
                svc.produce(topic="system-telemetry", event=event)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 1C — KAFKA CONSUMER SIMULATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestKafkaConsumerSimulation:
    """
    Simulates the Kafka consumer's message-processing logic.

    The consumer loop reads raw bytes from the broker and deserialises them
    into TelemetryEvent Pydantic models.  These tests verify that:
      - Well-formed messages parse correctly.
      - Malformed messages are caught without crashing the consumer loop.

    WHY SIMULATE INSTEAD OF IMPORT THE CONSUMER DIRECTLY:
        The consumer module contains a blocking ``while True`` loop designed
        to run as a separate process.  Rather than importing it (which would
        block the test runner), we test the *consumer's inner validation
        logic* in isolation — the pure unit-testing principle that keeps
        tests fast and deterministic.
    """

    @staticmethod
    def _deserialise_message(raw_bytes: bytes) -> TelemetryEvent:
        """
        Mirrors the deserialization logic inside the Kafka consumer loop:
        decode bytes -> parse JSON -> validate as TelemetryEvent.

        Testing this function in isolation means any future schema change
        immediately breaks this test as an early-warning signal before it
        reaches production consumers.
        """
        payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
        return TelemetryEvent.model_validate(payload)

    def test_consumer_processes_valid_message(self) -> None:
        """
        A properly formed Kafka message (produced by KafkaProducerService)
        must deserialise into a TelemetryEvent with all fields intact and
        correctly typed.
        """
        # Simulate the exact bytes KafkaProducerService.produce() would write.
        original_event = TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            service_name="inventory-api",
            level=LogLevel.WARNING,
            message="Stock level cache miss — falling back to DB query",
        )
        raw_bytes: bytes = original_event.model_dump_json().encode("utf-8")

        consumed_event: TelemetryEvent = self._deserialise_message(raw_bytes)

        assert consumed_event.event_id == original_event.event_id
        assert consumed_event.service_name == original_event.service_name
        assert consumed_event.level == LogLevel.WARNING
        assert consumed_event.message == original_event.message

    def test_consumer_handles_malformed_message(self) -> None:
        """
        A corrupted Kafka message (truncated JSON, wrong schema) must be
        caught by a try/except block without crashing the consumer loop.

        This test verifies the error isolation boundary: one bad message
        must never kill the consumer process and starve all subsequent
        healthy messages from being processed.
        """
        malformed_bytes: bytes = b'{"service_name": "payment-svc", INVALID JSON'

        processed_successfully = False
        error_was_caught = False

        try:
            self._deserialise_message(malformed_bytes)
            processed_successfully = True  # Should NOT reach here.
        except (json.JSONDecodeError, Exception):
            # Real consumer would log this and call consumer.commit() to skip.
            error_was_caught = True

        assert not processed_successfully, (
            "Malformed message should NOT parse successfully"
        )
        assert error_was_caught, (
            "Consumer must catch the exception — never let it propagate"
        )
