# app/core/logging.py
"""
Structured logging setup for SmartEnergy API.
Uses Loguru for human-readable (dev) and JSON (prod) output.
Correlates logs with OpenTelemetry trace IDs if available.
"""

from __future__ import annotations
import os
import sys
import json
import logging
from loguru import logger
from opentelemetry import trace


def _get_trace_id() -> str | None:
    """Return current OTel trace ID as hex string, if active."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return f"{ctx.trace_id:032x}"
    return None


def serialize(record: dict) -> str:
    """Serialize log record to compact JSON for production."""
    trace_id = _get_trace_id()
    payload = {
        "time": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    if trace_id:
        payload["trace_id"] = trace_id
    return json.dumps(payload)


def setup_logging(role: str | None = None) -> None:
    """Configure Loguru as the global logger."""
    # Remove default handler to avoid duplicates
    logger.remove()

    env = os.getenv("ENV", "dev")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    runtime_role = role or os.getenv("ROLE", "process")
    if runtime_role == "web":
        runtime_role = "api"
    logger.configure(extra={"role": runtime_role})

    if env == "prod":
        # Hosted processes emit structured logs only to stdout.
        logger.add(sys.stdout, level=log_level, enqueue=True, serialize=True)
    else:
        log_path = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_path, exist_ok=True)
        log_file = os.path.join(log_path, "app.log")
        # Development → colorful readable logs
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "{extra[role]} | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        logger.add(sys.stdout, format=fmt, level=log_level, enqueue=True)
        logger.add(
            log_file,
            rotation="1 day",
            retention="7 days",
            level=log_level,
            enqueue=True,
        )

    # Bridge stdlib logging (uvicorn, FastAPI, Celery)
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level_name: str = logger.level(record.levelname).name  # str
            except Exception:
                level_name = str(record.levelno)  # cast to str to unify types
            logger.opt(depth=6, exception=record.exc_info).log(
                level_name, record.getMessage()
            )

    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

    logger.info(
        "[logging] Initialized Loguru (env={}, level={}, role={})",
        env,
        log_level,
        runtime_role,
    )
