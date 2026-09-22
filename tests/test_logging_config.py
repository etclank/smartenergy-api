# tests/test_logging_config.py
import json
from app.core import logging as lg
from datetime import datetime


def test_setup_logging_dev(monkeypatch, tmp_path):
    """Dev environment → colorful formatter setup."""
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.chdir(tmp_path)
    lg.setup_logging()
    # Verify log file created under ./logs
    assert (tmp_path / "logs" / "app.log").exists()


def test_setup_logging_prod(monkeypatch, tmp_path):
    """Hosted logging uses structured stdout without a file sink."""
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.chdir(tmp_path)
    lg.setup_logging("worker")
    assert not (tmp_path / "logs").exists()


def test_serialize_includes_trace(monkeypatch):
    """serialize() returns JSON string with mandatory fields."""
    record = {
        "time": datetime.utcnow(),
        "level": type("Level", (), {"name": "INFO"})(),
        "message": "msg",
        "name": "mod",
        "function": "fn",
        "line": 10,
    }
    out = lg.serialize(record)
    data = json.loads(out)
    for field in ["time", "level", "message", "module", "function", "line"]:
        assert field in data
