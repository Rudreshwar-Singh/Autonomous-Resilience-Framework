"""
Telemetry Kafka Consumer Worker
================================
Standalone script that continuously polls the ``system-telemetry`` Kafka topic,
validates each message against the ``TelemetryEvent`` contract, and prints a
structured log to the terminal.

USAGE:
    # From the repo root, with the virtual environment activated:
    python -m backend.telemetry.consumer

    # Or as a direct script (if PYTHONPATH includes the repo root):
    python backend/telemetry/consumer.py

DESIGN DECISIONS:
    Standalone vs. embedded:
        The consumer runs as a *separate process*, not as a background
        asyncio task inside FastAPI.  This is a deliberate Modular Monolith
        boundary: the consumer is a read-side worker that belongs to the
        Telemetry domain's processing path, not to the HTTP ingestion path.
        In a future microservices split, it becomes its own deployable unit
        with zero code changes — just a new Dockerfile.

    confluent_kafka.Consumer:
        The librdkafka-backed Python client provides at-least-once delivery,
        configurable auto-commit, and sub-millisecond poll latency — all
        required properties for a reliable telemetry pipeline.

    Validation boundary:
        Every message is re-validated against ``TelemetryEvent`` even though
        the producer already validated before enqueuing.  This is intentional:
        the consumer is an independent trust boundary.  A future bad producer
        (different service, schema drift) should not corrupt downstream state.

GRACEFUL SHUTDOWN:
    The main loop catches ``KeyboardInterrupt`` (Ctrl+C / SIGINT) and calls
    ``consumer.close()`` before exiting, which commits the current offset and
    releases the consumer-group partition assignment cleanly.
"""

import json
import logging
import sys
from datetime import timezone

from confluent_kafka import Consumer, KafkaError, KafkaException, Message
from pydantic import ValidationError

from backend.contracts.events.telemetry import TelemetryEvent
from backend.core.settings import get_settings

# ── Bootstrap ─────────────────────────────────────────────────────────────────
# Configure a minimal human-readable logger for the terminal worker.
# In production, replace with the same structlog/loguru pipeline used in main.py.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger: logging.Logger = logging.getLogger("telemetry.consumer")

# ── Constants ─────────────────────────────────────────────────────────────────
_POLL_TIMEOUT_SECONDS: float = 1.0  # How long to block waiting for a message
_GROUP_ID: str = "arf-telemetry-consumer-group"


def _build_consumer(settings: object) -> Consumer:
    """
    Construct and return a configured ``confluent_kafka.Consumer``.

    Configuration decisions:
        - ``auto.offset.reset = earliest``: On first run (no committed offset),
          replay all historical messages so no events are missed during
          development restarts.
        - ``enable.auto.commit = true``: Offsets are committed automatically
          after each ``poll()`` call.  For at-least-once guarantees with manual
          commit, flip to ``false`` and call ``consumer.commit()`` after each
          successfully processed message.

    Args:
        settings: Application settings instance (``get_settings()``).

    Returns:
        An unsubscribed ``Consumer`` instance ready for ``.subscribe()``.
    """
    return Consumer(
        {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": _GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )


def _process_message(raw_msg: Message) -> None:
    """
    Decode, validate, and print a single Kafka message.

    Validation failures are logged as errors but do NOT raise — the consumer
    continues processing subsequent messages.  This prevents a single
    malformed event from stalling the entire pipeline.

    Args:
        raw_msg: A ``confluent_kafka.Message`` whose ``value()`` is a
                 UTF-8 encoded JSON bytes payload.
    """
    raw_bytes: bytes | None = raw_msg.value()
    if raw_bytes is None:
        logger.warning(
            "Received tombstone message — topic=%s partition=%s offset=%s",
            raw_msg.topic(),
            raw_msg.partition(),
            raw_msg.offset(),
        )
        return

    # ── Step 1: JSON decode ───────────────────────────────────────────
    try:
        payload: dict = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error(
            "Failed to decode message bytes as JSON — "
            "topic=%s partition=%s offset=%s error=%s",
            raw_msg.topic(),
            raw_msg.partition(),
            raw_msg.offset(),
            exc,
        )
        return

    # ── Step 2: Pydantic validation ───────────────────────────────────
    try:
        event = TelemetryEvent.model_validate(payload)
    except ValidationError as exc:
        logger.error(
            "TelemetryEvent validation FAILED — "
            "topic=%s partition=%s offset=%s errors=%s",
            raw_msg.topic(),
            raw_msg.partition(),
            raw_msg.offset(),
            exc.errors(),
        )
        return

    # ── Step 3: Structured terminal output ───────────────────────────
    # Normalise timestamp to UTC for consistent display regardless of producer TZ.
    ts_utc = event.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(
        f"\n{'-' * 72}\n"
        f"  * TELEMETRY EVENT RECEIVED\n"
        f"{'-' * 72}\n"
        f"  event_id    : {event.event_id}\n"
        f"  timestamp   : {ts_utc}\n"
        f"  service     : {event.service_name}\n"
        f"  level       : {event.level.value}\n"
        f"  message     : {event.message}\n"
        f"{'-' * 72}\n"
        f"  [Kafka]  topic={raw_msg.topic()}  "
        f"partition={raw_msg.partition()}  "
        f"offset={raw_msg.offset()}\n"
        f"{'-' * 72}",
        flush=True,
    )

    logger.debug(
        "Processed TelemetryEvent — event_id=%s service=%s level=%s",
        event.event_id,
        event.service_name,
        event.level.value,
    )


def run() -> None:
    """
    Main consumer loop — subscribe, poll, process, repeat.

    Execution flow:
        1. Load settings and build the Consumer.
        2. Subscribe to the telemetry topic.
        3. Enter the poll loop.
        4. On ``KeyboardInterrupt``, close the consumer gracefully and exit.
    """
    settings = get_settings()
    consumer = _build_consumer(settings)

    try:
        consumer.subscribe([settings.KAFKA_TOPIC_TELEMETRY])
        logger.info(
            "Consumer subscribed — topic=%s group=%s brokers=%s",
            settings.KAFKA_TOPIC_TELEMETRY,
            _GROUP_ID,
            settings.KAFKA_BOOTSTRAP_SERVERS,
        )
        logger.info("Waiting for messages… (press Ctrl+C to stop)")

        while True:
            msg: Message | None = consumer.poll(timeout=_POLL_TIMEOUT_SECONDS)

            if msg is None:
                # No message within the poll window — loop again.
                continue

            if msg.error():
                kafka_err: KafkaError = msg.error()
                if kafka_err.code() == KafkaError._PARTITION_EOF:
                    # Reached the end of a partition — not an error, just info.
                    logger.debug(
                        "End of partition reached — topic=%s partition=%s offset=%s",
                        msg.topic(),
                        msg.partition(),
                        msg.offset(),
                    )
                else:
                    logger.error("Kafka consumer error — %s", kafka_err)
                continue

            _process_message(msg)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received — shutting down consumer gracefully")

    finally:
        # Commit current offsets and release partition assignments cleanly.
        consumer.close()
        logger.info("Consumer closed — goodbye.")


if __name__ == "__main__":
    run()
