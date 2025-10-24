# app/core/telemetry.py
"""
OpenTelemetry bootstrap for SmartEnergy API.
Initializes tracing & metrics exporters if ENABLE_TELEMETRY=1.
"""

from __future__ import annotations
import os
import logging
from typing import Union

from fastapi import FastAPI

# Core OTel imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor


def init_telemetry(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing & metrics if enabled."""
    if os.getenv("ENABLE_TELEMETRY", "0") != "1":
        logging.info("[telemetry] Telemetry disabled by environment.")
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "smartenergy-api")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")

    resource = Resource.create({SERVICE_NAME: service_name})

    # ---- TRACES ----
    tracer_provider = TracerProvider(resource=resource)

    exporter: Union[OTLPSpanExporter, ConsoleSpanExporter]
    if otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=(dict([h.split("=", 1) for h in otlp_headers.split(",")]) if otlp_headers else None),
        )
        logging.info(f"[telemetry] OTLP trace exporter → {otlp_endpoint}")
    else:
        exporter = ConsoleSpanExporter()
        logging.info("[telemetry] Using ConsoleSpanExporter (no OTLP endpoint).")

    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    # ---- METRICS ----
    if otlp_endpoint:
        metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
        reader = PeriodicExportingMetricReader(metric_exporter)
        metrics_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(metrics_provider)
        logging.info("[telemetry] OTLP metric exporter configured.")
    else:
        logging.info("[telemetry] Metrics export skipped (no OTLP endpoint).")

    # ---- INSTRUMENTATION ----
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    # SQLAlchemy is instrumented where engine is created (see db.py) – safe no-op if repeated
    try:
        from app.core.db import engine
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except Exception as exc:
        logging.warning(f"[telemetry] SQLAlchemy instrumentation skipped: {exc}")

    logging.info(f"[telemetry] Initialized OpenTelemetry for service={service_name}")
