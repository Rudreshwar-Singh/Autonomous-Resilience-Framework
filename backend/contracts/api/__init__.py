"""
Contracts — API Layer
====================
Public Pydantic v2 models that define the HTTP request/response schemas
for every agent-facing REST endpoint.

These models are the single source of truth for the API surface.  They
are intentionally kept free of business logic so they can be safely
imported by any domain (agent, analysis, telemetry) without creating
circular dependencies.
"""
