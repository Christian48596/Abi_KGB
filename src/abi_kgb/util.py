from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional


def run_capture(cmd: list[str], *, cwd: Optional[Path] = None, timeout: int = 10, env=None) -> str:
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        return p.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def env_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if not raw:
        return None
    m = re.search(r"\d+", raw)
    return int(m.group()) if m else None


def parse_memory_gib(text: str) -> Optional[float]:
    """Parse common scheduler memory strings into GiB."""
    if not text:
        return None
    s = text.strip().lower().replace("ib", "b")
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmgt]?b?)?", s)
    if not m:
        return None
    value = float(m.group(1))
    unit = (m.group(2) or "").strip()
    if unit in ("", "b"):
        # Scheduler fields with no suffix are commonly bytes only in explicit byte-valued contexts.
        return value / 1024**3 if value > 1024**2 else value
    if unit in ("k", "kb"):
        return value / 1024**2
    if unit in ("m", "mb"):
        return value / 1024
    if unit in ("g", "gb"):
        return value
    if unit in ("t", "tb"):
        return value * 1024
    return None
