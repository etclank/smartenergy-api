from __future__ import annotations
from datetime import datetime
from pathlib import Path
from app.core.config import settings
import shutil
import os

async def backup_db_snapshot() -> dict:
    """
    Create a lightweight DB snapshot file for demo/testing.
    Uses /app/backups in Docker, but falls back to ./backups locally.
    """
    # Prefer /app/backups (container), fallback for local tests
    default_dir = Path("/app/backups")
    local_dir = Path("./backups")

    backups_dir = default_dir if default_dir.exists() and os.access(default_dir.parent, os.W_OK) else local_dir
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = backups_dir / f"snapshot_{timestamp}.db"

    src = settings.database_url.replace("sqlite+aiosqlite:///", "")
    try:
        if src and Path(src).exists():
            shutil.copy(src, target)
            return {"status": "ok", "backup_file": str(target)}
        else:
            # No file yet in memory DB
            target.touch()
            return {"status": "ok", "backup_file": str(target), "note": "empty DB created"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
