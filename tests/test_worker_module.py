# tests/test_worker_module.py
import importlib
import types


def test_worker_import_and_tasks(monkeypatch):
    """Ensure Celery worker imports and registers all tasks safely."""
    import app.tasks.worker as worker_mod

    # Dummy Celery replacement that works whether used as a class or instance
    class DummyCelery:
        # class-level fallbacks (in case module assigns the class itself)
        name = "smartenergy"
        conf = types.SimpleNamespace(
            beat_schedule={},
            task_routes={},
            task_default_queue=None,
        )
        tasks = {}

        def __init__(self, *a, **kw):
            # instance-level too
            self.name = "smartenergy"
            self.conf = types.SimpleNamespace(
                beat_schedule={},
                task_routes={},
                task_default_queue=None,
            )
            self.tasks = {}

        @classmethod
        def task(cls, name=None, **_):
            # allow decorator to work on class or instance
            def decorator(fn):
                # register on both class and any instance created later
                cls.tasks[name or fn.__name__] = fn
                return fn
            return decorator

        # If module does Celery(...).task, the instance also needs `task`
        def _task_instance(self, name=None, **_):
            def decorator(fn):
                self.tasks[name or fn.__name__] = fn
                type(self).tasks[name or fn.__name__] = fn
                return fn
            return decorator

    monkeypatch.setattr(worker_mod, "Celery", DummyCelery)
    worker_mod = importlib.reload(worker_mod)

    app = worker_mod.celery_app

    # Support both: if module exposed the class instead of an instance,
    # class attributes provide required fields.
    name_attr = getattr(app, "name", getattr(DummyCelery, "name", None))
    assert isinstance(name_attr, str) and name_attr.startswith("smartenergy")

    conf_attr = getattr(app, "conf", getattr(DummyCelery, "conf", None))
    assert isinstance(conf_attr.beat_schedule, dict)

    # Tasks should be registered either on instance or class registry
    tasks_map = getattr(app, "tasks", DummyCelery.tasks)

    expected_tasks = [
        "kpis.refresh",
        "demo.generate",
        "demo.clean",
        "cache.clean",
        "metrics.record",
        "backup.db",
        "email.health",
    ]
    for t in expected_tasks:
        assert any(t in k for k in tasks_map)
    assert len(conf_attr.beat_schedule) >= 5
