from __future__ import annotations

import re
import shutil

from ..models import AbinitInfo
from ..util import run_capture


def detect_abinit(executable: str | None = None) -> AbinitInfo:
    path = shutil.which(executable) if executable else shutil.which("abinit")
    if executable and not path:
        path = executable
    if not path:
        return AbinitInfo(None, None)
    version_text = run_capture([path, "--version"], timeout=10)
    first = next((x.strip() for x in version_text.splitlines() if x.strip()), None)
    version = None
    if first:
        m = re.search(r"\d+\.\d+(?:\.\d+)?(?:[-A-Za-z0-9.]*)?", first)
        version = m.group(0) if m else first
    # ABINIT prints build information during normal startup; --build is not guaranteed.
    build = run_capture([path, "--build"], timeout=10)
    combined = (version_text + "\n" + build).lower()
    mpi = True if "mpi" in combined else None
    omp = True if "openmp" in combined and "no openmp" not in combined else None
    gpu = True if any(x in combined for x in ("cuda", "hip", "gpu support    : yes")) else None
    return AbinitInfo(path, version, build_text=build, mpi_enabled=mpi, openmp_enabled=omp, gpu_enabled=gpu)
