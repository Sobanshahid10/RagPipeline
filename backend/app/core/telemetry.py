"""OpenTelemetry tracer setup for the RAG pipeline.

Exports OTLP spans to Jaeger (or any compatible collector) and
auto-instruments FastAPI + asyncpg.  Call ``setup_telemetry(app)``
once from main.py on startup to activate tracing.
"""

from __future__ import annotations

import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

# Module-level singleton – returned by setup_telemetry() and reused everywhere.
_tracer: trace.Tracer | None = None


def setup_telemetry(app) -> trace.Tracer:
    """Configure OpenTelemetry tracing, instrument FastAPI, and return the tracer.

    Safe to call multiple times – subsequent calls are no-ops that return the
    already-configured tracer.
    """
    global _tracer
    if _tracer is not None:
        return _tracer

    resource = Resource.create({"service.name": "rag.pipeline", "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)

    # ── OTLP gRPC exporter (sends to Jaeger / any OTEL collector) ──────────
    otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://localhost:4317")
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OpenTelemetry OTLP exporter active → %s", otlp_endpoint)
    except Exception as exc:  # pragma: no cover
        # If the gRPC exporter is not installed / reachable we fall back to a
        # no-op exporter so that spans are still created and timed locally.
        logger.warning("OTLP exporter unavailable (%s) – tracing spans will not be exported.", exc)

    trace.set_tracer_provider(provider)

    # ── Auto-instrument FastAPI ─────────────────────────────────────────────
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OpenTelemetry instrumentation active.")
    except Exception as exc:  # pragma: no cover
        logger.warning("FastAPI instrumentation failed: %s", exc)

    # ── Auto-instrument asyncpg ─────────────────────────────────────────────
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

        AsyncPGInstrumentor().instrument()
        logger.info("asyncpg OpenTelemetry instrumentation active.")
    except Exception as exc:  # pragma: no cover
        logger.warning("asyncpg instrumentation failed: %s", exc)

    _tracer = trace.get_tracer("rag.pipeline")
    return _tracer


def get_tracer() -> trace.Tracer:
    """Return the module-level tracer (no-op if setup_telemetry was never called)."""
    global _tracer
    if _tracer is None:
        # Return a no-op tracer so callers never have to guard against None.
        _tracer = trace.get_tracer("rag.pipeline")
    return _tracer
