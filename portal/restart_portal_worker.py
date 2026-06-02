"""Detached one-shot: wait, kill port listener, start server.py."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def kill_port(port: int) -> None:
    if sys.platform == "win32":
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids: set[int] = set()
        needle = f":{port} "
        for line in out.stdout.splitlines():
            if "LISTENING" not in line or needle not in line:
                continue
            parts = line.split()
            if parts:
                try:
                    pids.add(int(parts[-1]))
                except ValueError:
                    pass
        for pid in pids:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                check=False,
            )
        return

    subprocess.run(
        ["fuser", "-k", f"{port}/tcp"],
        capture_output=True,
        check=False,
    )


def main() -> None:
    portal_root = Path(os.environ["PORTAL_ROOT"])
    port = int(os.environ.get("PORTAL_PORT", "8080"))
    python = os.environ.get("PORTAL_PYTHON", sys.executable)

    time.sleep(2)
    kill_port(port)
    time.sleep(1)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(
        [python, "server.py"],
        cwd=str(portal_root),
        creationflags=creationflags,
    )


if __name__ == "__main__":
    main()
