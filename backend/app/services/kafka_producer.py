"""
Kafka Producer Service
======================
Provides a thin, lifecycle-managed wrapper around ``confluent_kafka.Producer``
for use inside the FastAPI application.

WHY A SERVICE CLASS (not a module-level function):
    The ``confluent_kafka.Producer`` maintains an internal network socket and
    a delivery-report queue.  Instantiating it at module import time would
    connect to the broker before logging is even configured, and would make
    unit testing impossible without a real broker.  Wrapping it in a class
    lets the lifespan context manager control *when* the connection is
    established and *when* it is torn down — matching FastAPI's startup/shutdown
    lifecycle precisely.

NON-BLOCKING DESIGN:
    ``confluent_kafka.Producer.produce()`` is synchronous under the hood, but
    it enqueues messages in librdkafka's internal buffer rather than doing a
    network round-trip.  The call to ``poll(0)`` after each produce drains
    any pending delivery callbacks without blocking, which is safe to call
    from an async route handler because it never suspends the event loop.

    If you need genuine async backpressure (e.g., >50k msg/s), the pattern
    to adopt is: run ``poll()`` inside ``asyncio.get_event_loop().run_in_executor``
    so librdkafka's blocking poll happens on a thread-pool thread, not the
    event loop thread.  For this MVP throughput profile, ``poll(0)`` is
    sufficient and adds zero latency.
"""

import json
import logging
from typing import TYPE_CHECKING

from confluent_kafka import KafkaException, Producer

if TYPE_CHECKING:
    from backend.contracts.events.telemetry import TelemetryEvent

logger: logging.Logger = logging.getLogger(__name__)


class KafkaProducerService:
    """
    Lifecycle-managed Kafka producer for the ARF backend.

    Lifecycle:
        1. Instantiate in ``main.py``'s lifespan (before ``yield``).
        2. Inject into routers via FastAPI's dependency system or app.state.
        3. Call ``flush()`` + ``close()`` after ``yield`` in lifespan.

    Thread-safety:
        ``confluent_kafka.Producer`` is *not* thread-safe; however FastAPI's
        default async mode runs all route coroutines on a single event-loop
        thread, so a single shared instance is safe here.  If sync background
        threads are added in a future phase, wrap produce calls with a
        threading.Lock.
    """

    def __init__(self, bootstrap_servers: str) -> None:
        """
        Creates and connects the underlying librdkafka producer.

        Args:
            bootstrap_servers: Comma-separated Kafka broker addresses,
                               e.g. "localhost:9092" or "broker1:9092,broker2:9092".
        """
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                # Delivery acknowledgement from the leader replica only.
                # "all" would require replication factor > 1 (single-node dev Kafka
                # doesn't have replicas), so "1" is the correct setting here.
                "acks": "1",
                # Compress batches with snappy for network efficiency once
                # throughput grows beyond single-digit msg/s.
                "compression.type": "snappy",
                # Log delivery errors at the library level so they surface
                # in structured logs without extra callback wiring.
                "error_cb": self._on_error,
            }
        )
        logger.info(
            "KafkaProducerService initialised — bootstrap_servers=%s",
            bootstrap_servers,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def produce(self, topic: str, event: "TelemetryEvent") -> None:
        """
        Serialise ``event`` to JSON and enqueue it for delivery to ``topic``.

        This method is intentionally non-blocking:
        - ``producer.produce()`` writes to librdkafka's internal buffer.
        - ``producer.poll(0)`` flushes any *already-completed* delivery
          callbacks without waiting for new ones — zero I/O block.

        Args:
            topic: Kafka topic name (e.g. "system-telemetry").
            event: A validated ``TelemetryEvent`` Pydantic model instance.

        Raises:
            KafkaException: If the internal buffer is full (``BufferError``)
                            or the broker is unreachable at enqueue time.
        """
        payload: bytes = event.model_dump_json().encode("utf-8")
        key: bytes = event.service_name.encode("utf-8")

        try:
            self._producer.produce(
                topic=topic,
                key=key,
                value=payload,
                on_delivery=self._delivery_report,
            )
            # Drain already-completed delivery callbacks — non-blocking (timeout=0).
            self._producer.poll(0)
        except KafkaException as exc:
            logger.error(
                "Failed to enqueue telemetry event — event_id=%s error=%s",
                event.event_id,
                exc,
            )
            raise

        logger.debug(
            "Telemetry event enqueued — event_id=%s service=%s topic=%s",
            event.event_id,
            event.service_name,
            topic,
        )

    def flush(self, timeout: float = 10.0) -> None:
        """
        Block until all enqueued messages are delivered or ``timeout`` expires.

        Called during application shutdown to guarantee no messages are lost
        in the internal buffer when the process exits.

        Args:
            timeout: Maximum seconds to wait for in-flight messages to drain.
        """
        remaining = self._producer.flush(timeout=timeout)
        if remaining > 0:
            logger.warning(
                "KafkaProducerService flush timed out — %d message(s) may be lost",
                remaining,
            )
        else:
            logger.info("KafkaProducerService flush complete — all messages delivered")

    def close(self) -> None:
        """
        Alias for ``flush()`` with a short timeout, signalling teardown intent.

        Provided as a semantic alias so lifespan shutdown code reads naturally:
            producer.flush()
            producer.close()
        """
        logger.info("KafkaProducerService shutting down")
        self.flush(timeout=5.0)

    # ── Private Callbacks ─────────────────────────────────────────────────────

    @staticmethod
    def _delivery_report(err: object, msg: object) -> None:
        """
        librdkafka delivery callback — fired when a message is acknowledged
        or permanently failed.  Runs on the thread that calls ``poll()``.

        Args:
            err: None on success; a KafkaError instance on failure.
            msg: The Message object that was delivered (or failed).
        """
        if err is not None:
            logger.error(
                "Kafka delivery FAILED — topic=%s partition=%s error=%s",
                getattr(msg, "topic", lambda: "unknown")(),
                getattr(msg, "partition", lambda: -1)(),
                err,
            )
        else:
            logger.debug(
                "Kafka delivery OK — topic=%s partition=%s offset=%s",
                msg.topic(),  # type: ignore[union-attr]
                msg.partition(),  # type: ignore[union-attr]
                msg.offset(),  # type: ignore[union-attr]
            )

    @staticmethod
    def _on_error(err: object) -> None:
        """
        Global error callback for non-fatal broker-level errors (e.g. leader
        elections, metadata refreshes).  These do not lose messages but are
        worth surfacing in structured logs.
        """
        logger.warning("Kafka client error (non-fatal) — %s", err)
