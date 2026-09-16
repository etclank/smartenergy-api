import importlib
import types


class DummyApp:
    pass


def test_telemetry_disabled(monkeypatch, caplog):
    """When ENABLE_TELEMETRY != 1 → no init occurs."""
    monkeypatch.delenv("ENABLE_TELEMETRY", raising=False)
    caplog.set_level("INFO")
    from app.core import telemetry

    importlib.reload(telemetry)
    telemetry.init_telemetry(DummyApp())
    assert any("disabled" in m.lower() for m in caplog.messages)


def test_telemetry_enabled_console(monkeypatch):
    """ENABLE_TELEMETRY=1 but no OTLP endpoint → Console exporter."""
    monkeypatch.setenv("ENABLE_TELEMETRY", "1")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    from app.core import telemetry

    monkeypatch.setattr(
        telemetry,
        "TracerProvider",
        lambda *a, **k: types.SimpleNamespace(add_span_processor=lambda *_: None),
    )
    monkeypatch.setattr(telemetry, "BatchSpanProcessor", lambda *_: None)
    monkeypatch.setattr(telemetry, "ConsoleSpanExporter", lambda *_: object())
    monkeypatch.setattr(
        telemetry,
        "FastAPIInstrumentor",
        types.SimpleNamespace(instrument_app=lambda *_: None),
    )
    monkeypatch.setattr(
        telemetry,
        "HTTPXClientInstrumentor",
        lambda *_: types.SimpleNamespace(instrument=lambda *_: None),
    )
    monkeypatch.setattr(
        telemetry,
        "RedisInstrumentor",
        lambda *_: types.SimpleNamespace(instrument=lambda *_: None),
    )
    monkeypatch.setattr(
        telemetry,
        "SQLAlchemyInstrumentor",
        lambda *_: types.SimpleNamespace(instrument=lambda *_: None),
    )

    telemetry.init_telemetry(DummyApp())


def test_telemetry_enabled_otlp(monkeypatch):
    """ENABLE_TELEMETRY=1 + endpoint → OTLP exporters branch."""
    monkeypatch.setenv("ENABLE_TELEMETRY", "1")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://example.com")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Bearer 123")

    from app.core import telemetry

    class DummyReader:
        """Minimal fake reader compatible with OpenTelemetry MeterProvider."""

        _instrument_class_temporality = {}
        _instrument_class_aggregation = {}

        def __init__(self, *a, **k):
            self._cb = None

        def _set_collect_callback(self, cb):
            self._cb = cb

        def shutdown(self, **kwargs):
            # Accept optional keyword args (like timeout_millis)
            return None

    # Patch exporters and providers
    monkeypatch.setattr(telemetry, "OTLPSpanExporter", lambda *a, **k: object())
    monkeypatch.setattr(telemetry, "OTLPMetricExporter", lambda *a, **k: object())
    monkeypatch.setattr(
        telemetry, "PeriodicExportingMetricReader", lambda *a, **k: DummyReader()
    )
    monkeypatch.setattr(
        telemetry,
        "TracerProvider",
        lambda *a, **k: types.SimpleNamespace(add_span_processor=lambda *_: None),
    )
    monkeypatch.setattr(telemetry, "BatchSpanProcessor", lambda *_: None)
    monkeypatch.setattr(
        telemetry,
        "FastAPIInstrumentor",
        types.SimpleNamespace(instrument_app=lambda *_: None),
    )
    monkeypatch.setattr(
        telemetry,
        "HTTPXClientInstrumentor",
        lambda *_: types.SimpleNamespace(instrument=lambda *_: None),
    )
    monkeypatch.setattr(
        telemetry,
        "RedisInstrumentor",
        lambda *_: types.SimpleNamespace(instrument=lambda *_: None),
    )
    monkeypatch.setattr(
        telemetry,
        "SQLAlchemyInstrumentor",
        lambda *_: types.SimpleNamespace(instrument=lambda *_: None),
    )

    telemetry.init_telemetry(DummyApp())
