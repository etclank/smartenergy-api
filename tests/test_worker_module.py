from app.tasks.worker import celery_app


def test_worker_tasks_and_reliability_configuration():
    expected_tasks = {
        "system.ping",
        "kpis.refresh",
        "demo.generate",
        "demo.clean",
        "cache.clean",
        "metrics.record",
        "meta.update",
        "email.health",
    }
    assert expected_tasks.issubset(celery_app.tasks)
    assert "cache.warmup" not in celery_app.tasks
    assert "backup.db" not in celery_app.tasks

    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_track_started is True


def test_default_beat_schedule_contains_only_reviewed_tasks():
    scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
    assert scheduled == {"kpis.refresh", "cache.clean", "metrics.record"}
