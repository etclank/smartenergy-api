import os
from pathlib import Path
import subprocess

import pytest


PRESTART = Path(__file__).parents[1] / "scripts" / "prestart.sh"


def _fake_command(directory: Path, name: str) -> None:
    command = directory / name
    command.write_text(f"#!/bin/sh\nprintf '{name}|%s\\n' \"$*\"\n")
    command.chmod(0o755)


def _run_prestart(tmp_path: Path, role: str) -> subprocess.CompletedProcess[str]:
    _fake_command(tmp_path, "uvicorn")
    _fake_command(tmp_path, "celery")
    env = os.environ.copy()
    env.update(ROLE=role, PATH=f"{tmp_path}:{env['PATH']}")
    return subprocess.run(
        [str(PRESTART)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_prestart_rejects_unsupported_role(tmp_path: Path) -> None:
    result = _run_prestart(tmp_path, "unsupported")

    assert result.returncode == 64
    assert result.stdout == ""
    assert result.stderr == "Unsupported ROLE: unsupported\n"


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("web", "uvicorn|app.main:app --host 0.0.0.0 --port 8000\n"),
        (
            "worker",
            "celery|-A app.tasks.worker.celery_app worker --concurrency=1 "
            "--loglevel=info\n",
        ),
        (
            "beat",
            "celery|-A app.tasks.worker.celery_app beat --loglevel=info "
            "--schedule=/tmp/celerybeat-schedule\n",
        ),
    ],
)
def test_prestart_launches_supported_role(
    tmp_path: Path, role: str, expected: str
) -> None:
    result = _run_prestart(tmp_path, role)

    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""
