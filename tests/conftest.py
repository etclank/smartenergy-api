# tests/conftest.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
