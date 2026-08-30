from __future__ import annotations

import re
import shutil

from ..models import MpiInfo
from ..util import run_capture


def _family(text: str) -> str:
    low = text.lower()
    if "open mpi" in low or "open-mpi" in low:
        return "openmpi"
    if "intel(r) mpi" in low or "intel mpi" in low:
        return "intelmpi"
    if "cray mpich" in low or "cray-mpich" in low:
        return "cray-mpich"
    if "mvapich" in low:
        return "mvapich"
    if "hydra build details" in low or "mpich version" in low or "version:" in low and "hydra" in low:
        return "mpich"
    return "unknown"


def _hydra_launchers(text: str) -> tuple[str, ...]:
    for line in text.splitlines():
        if "Launchers available:" in line:
            return tuple(line.split(":", 1)[1].strip().split())
    return ()


def _slurm_plugins() -> tuple[str, ...]:
    if not shutil.which("srun"):
        return ()
    text = run_capture(["srun", "--mpi=list"], timeout=5)
    values: list[str] = []
    for line in text.splitlines():
        if ":" in line:
            tail = line.split(":", 1)[1]
            values.extend(re.findall(r"[A-Za-z0-9_-]+", tail))
    return tuple(dict.fromkeys(values))


def detect_mpi(preferred: str | None = None) -> MpiInfo:
    path = None
    if preferred and preferred != "auto":
        path = shutil.which(preferred) or preferred
    else:
        path = shutil.which("mpiexec") or shutil.which("mpirun")
    if not path:
        return MpiInfo(None, None, "none", None, (), _slurm_plugins())
    text = run_capture([path, "--version"], timeout=5)
    if not text:
        text = run_capture([path, "-version"], timeout=5)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return MpiInfo(
        launcher_path=path,
        launcher_name=path.rsplit("/", 1)[-1],
        family=_family(text),
        version_line=lines[0] if lines else None,
        hydra_launchers=_hydra_launchers(text),
        slurm_mpi_plugins=_slurm_plugins(),
    )
