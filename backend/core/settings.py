"""
Application Settings Module
============================
Centralized configuration management using Pydantic BaseSettings.

WHY THIS DESIGN:
    Pydantic BaseSettings automatically reads from environment variables,
    making the app configurable without code changes. This is critical for
    a system that will eventually run across Docker containers where each
    service needs different config values (Kafka brokers, Prometheus ports, etc.).

    By defining all settings here with sensible defaults, local development
    "just works" out of the box on Windows 11 — no .env file required to boot.

FUTURE EXTENSIBILITY:
    As new phases are built, add new fields here:
    - Phase 5 (Current): KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_TELEMETRY
    - Phase 6: PROMETHEUS_PORT, GRAFANA_URL
    - Phase 7: GEMINI_API_KEY, GEMINI_MODEL (now implemented)
"""

from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application-wide configuration with environment variable overrides.

    All settings can be overridden by setting the corresponding environment
    variable (case-insensitive). For example:
        set APP_NAME=MyCustomName     (Windows CMD)
        $env:APP_NAME="MyCustomName"  (PowerShell)

    Attributes:
        APP_NAME: Display name used in OpenAPI docs and structured logs.
        APP_VERSION: Semantic version string for the API.
        DEBUG: Enables verbose logging and debug-level log output.
        API_V1_PREFIX: URL prefix for all versioned API endpoints.
        ALLOWED_ORIGINS: CORS origins permitted for frontend communication.
        LOG_LEVEL: Minimum severity level for structured log output.
        LOG_FORMAT: Output format for logs — 'json' for machine parsing,
                    'text' for local development readability.
        KAFKA_BOOTSTRAP_SERVERS: Comma-separated list of Kafka broker addresses.
                                  Matches the Docker-Compose service on port 9092
                                  for local dev; override per environment.
        KAFKA_TOPIC_TELEMETRY: The Kafka topic name for inbound telemetry events.
        GEMINI_API_KEY: Google Gemini API key (free-tier). Set via environment
                        variable ``GEMINI_API_KEY`` or in a local ``.env`` file.
                        Per 98_project_constraints.md, only free-tier APIs are
                        permitted — never commit this value to source control.
        GEMINI_MODEL: The Gemini model identifier used by the Decision Engine.
                      Defaults to ``gemini-2.5-flash`` for speed and free-tier
                      availability. Override per environment if needed.
    """

    # ── Application Identity ──────────────────────────────────────────
    APP_NAME: str = "Autonomous Resilience Framework"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── API Configuration ─────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS — Frontend Origins ───────────────────────────────────────
    # Default allows local Next.js dev server; extend for production.
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",   # Next.js fallback port when 3000 is in use
        "http://127.0.0.1:3001",
    ]

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "json"  # 'json' for pipeline compatibility, 'text' for dev

    # ── Kafka ─────────────────────────────────────────────────────────
    # Matches the Dockerised broker defined in infra/docker-compose.yml.
    # Override via environment variable for staging/production brokers.
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_TELEMETRY: str = "system-telemetry"

    # ── Phase 7: AI Decision Engine ───────────────────────────────────
    # GEMINI_API_KEY is intentionally blank by default so the application
    # boots without a key in non-agent contexts (health checks, graph
    # analysis).  The DecisionEngine validates its presence at call time,
    # not at startup — keeping the server lightweight.
    #
    # Set via PowerShell: $env:GEMINI_API_KEY="AIza..."
    # or via .env file:   GEMINI_API_KEY=AIza...
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── Pydantic Model Configuration ──────────────────────────────────
    # Tells Pydantic to read from a .env file if one exists, and to
    # match environment variables case-insensitively.
    model_config: ClassVar[dict] = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of the application settings.

    WHY CACHED:
        Settings are read once at startup and never change during runtime.
        Using lru_cache avoids re-parsing environment variables on every
        request, which matters when this function is used as a FastAPI
        dependency across dozens of endpoints.

    Returns:
        Settings: The validated, immutable application configuration.
    """
    return Settings()
