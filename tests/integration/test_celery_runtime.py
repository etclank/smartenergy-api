from __future__ import annotations

import os

import pytest

broker_url = os.environ.get("TEST_CELERY_BROKER_URL")
result_url = os.environ.get("TEST_CELERY_RESULT_URL")
if not broker_url or not result_url:
    pytest.skip(
        "Celery test broker and result URLs are required", allow_module_level=True
    )

os.environ["CELERY_BROKER_URL"] = broker_url
os.environ["CELERY_RESULT_BACKEND"] = result_url

from app.tasks.celery_app import celery_app  # noqa: E402


@pytest.mark.celery
def test_worker_receives_and_completes_task() -> None:
    result = celery_app.send_task("system.ping", args=["stage2"])
    assert result.get(timeout=15) == {"status": "ok", "value": "stage2"}
    assert result.state == "SUCCESS"
    result.forget()
