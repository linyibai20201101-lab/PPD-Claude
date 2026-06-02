"""Portal admin utilities — local restart, boot info."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

PORTAL_PORT = int(os.getenv("PORTAL_PORT", "8080"))
SERVER_BOOT_ID = uuid.uuid4().hex[:8]
SERVER_STARTED_AT = time.time()


def is_local_client(host: str | None) -> bool:
    if not host:
        return False
    return host in ("127.0.0.1", "::1", "localhost")


def portal_info() -> dict:
    return {
        "boot_id": SERVER_BOOT_ID,
        "started_at": SERVER_STARTED_AT,
        "port": PORTAL_PORT,
        "python": sys.executable,
    }


def schedule_restart(portal_root: Path, port: int = PORTAL_PORT) -> None:
    """Spawn detached worker: wait → kill port → start server.py."""
    root = portal_root.resolve()
    worker = root / "restart_portal_worker.py"
    if not worker.is_file():
        raise FileNotFoundError(f"缺少重启脚本: {worker}")

    env = os.environ.copy()
    env["PORTAL_PORT"] = str(port)
    env["PORTAL_PYTHON"] = sys.executable
    env["PORTAL_ROOT"] = str(root)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        [sys.executable, str(worker)],
        cwd=str(root),
        env=env,
        creationflags=creationflags,
        close_fds=True,
    )
