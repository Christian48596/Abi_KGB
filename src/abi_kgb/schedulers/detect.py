from __future__ import annotations

import os
import shutil

from ..models import ResourceEnvelope, SchedulerInfo, SystemInfo
from .base import SchedulerBackend
from .local import LocalBackend
from .pbs import PbsBackend
from .slurm import SlurmBackend


def detect_scheduler(requested: str = "auto", *, partition: str | None = None,
                     queue: str | None = None) -> tuple[SchedulerBackend, SchedulerInfo]:
    req = requested.lower()
    if req not in {"auto", "local", "slurm", "pbs"}:
        raise ValueError("scheduler must be auto, local, slurm, or pbs")
    if req == "slurm":
        b = SlurmBackend(); return b, b.info()
    if req == "pbs":
        b = PbsBackend(); return b, b.info()
    if req == "local":
        b = LocalBackend(); return b, b.info()
    if "SLURM_JOB_ID" in os.environ:
        b = SlurmBackend(); return b, b.info()
    if "PBS_JOBID" in os.environ:
        b = PbsBackend(); return b, b.info()
    if partition:
        b = SlurmBackend(); return b, b.info()
    if queue:
        b = PbsBackend(); return b, b.info()
    b = LocalBackend(); return b, b.info()


def resource_envelope(backend: SchedulerBackend, system: SystemInfo, **kwargs) -> ResourceEnvelope:
    return backend.resources(system, **kwargs)
