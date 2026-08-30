from __future__ import annotations

import collections
import os
import re
import shutil
from pathlib import Path

from ..models import ResourceEnvelope, SchedulerInfo, SystemInfo
from ..util import parse_memory_gib, run_capture
from .base import SchedulerBackend


def _pbs_flavor() -> str:
    text = ""
    for cmd in (["qstat", "--version"], ["pbsnodes", "--version"], ["qstat", "-Bf"]):
        if shutil.which(cmd[0]):
            text += "\n" + run_capture(cmd, timeout=5)
    low = text.lower()
    if "torque" in low:
        return "torque"
    if "openpbs" in low:
        return "openpbs"
    if "pbspro" in low or "pbs professional" in low:
        return "pbspro"
    return "pbs"


def _nodefile_shape(nodefile: str | None) -> tuple[int | None, int | None, int | None]:
    if not nodefile:
        return None, None, None
    try:
        hosts = [x.strip() for x in Path(nodefile).read_text().splitlines() if x.strip()]
    except OSError:
        return None, None, None
    if not hosts:
        return None, None, None
    counts = collections.Counter(hosts)
    return len(counts), sum(counts.values()), max(counts.values())


def _job_memory(jobid: str | None) -> float | None:
    if not jobid or not shutil.which("qstat"):
        return None
    text = run_capture(["qstat", "-f", jobid], timeout=10)
    # Prefer per-chunk mem in select if present; otherwise total Resource_List.mem.
    m = re.search(r"Resource_List\.select\s*=.*?mem=([^:+\s]+)", text, re.I)
    if m:
        return parse_memory_gib(m.group(1))
    m = re.search(r"Resource_List\.mem\s*=\s*([^\s]+)", text, re.I)
    return parse_memory_gib(m.group(1)) if m else None


def _queue_resources(queue: str | None) -> tuple[int | None, float | None]:
    if not queue or not shutil.which("qstat"):
        return None, None
    text = run_capture(["qstat", "-Qf", queue], timeout=10)
    ncpus = None
    mem = None
    m = re.search(r"resources_default\.select\s*=.*?ncpus=(\d+)", text, re.I)
    if m:
        ncpus = int(m.group(1))
    m = re.search(r"resources_default\.select\s*=.*?mem=([^:+\s]+)", text, re.I)
    if m:
        mem = parse_memory_gib(m.group(1))
    return ncpus, mem


class PbsBackend(SchedulerBackend):
    kind = "pbs"

    def info(self) -> SchedulerInfo:
        active = "PBS_JOBID" in os.environ
        nodefile = os.environ.get("PBS_NODEFILE")
        return SchedulerInfo(
            kind="pbs",
            active_allocation=active,
            flavor=_pbs_flavor(),
            job_id=os.environ.get("PBS_JOBID"),
            partition_or_queue=os.environ.get("PBS_QUEUE"),
            submit_dir=os.environ.get("PBS_O_WORKDIR"),
            nodefile=nodefile,
        )

    def resources(self, system: SystemInfo, *, nodes=None, max_cpus=None,
                  ranks_per_node=None, memory_per_node=None,
                  partition_or_queue=None, allow_smt=False) -> ResourceEnvelope:
        info = self.info()
        nf_nodes, nf_total, nf_rpn = _nodefile_shape(info.nodefile)
        if info.active_allocation:
            n = nodes or nf_nodes or 1
            total = max_cpus or nf_total
            rpn = ranks_per_node or nf_rpn
            if total is None:
                rpn = rpn or (system.physical_cores or system.logical_cpus)
                total = n * rpn
            if rpn is None:
                rpn = max(1, total // n)
            mem = memory_per_node if memory_per_node is not None else _job_memory(info.job_id)
            return ResourceEnvelope(
                nodes=n, max_total_ranks=total, max_ranks_per_node=rpn,
                memory_per_node_gib=mem,
                source="active PBS allocation/PBS_NODEFILE",
                physical_cores_per_node=None,
                logical_cpus_per_node=rpn,
            )
        queue = partition_or_queue
        qcpus, qmem = _queue_resources(queue)
        n = nodes or 1
        rpn = ranks_per_node or qcpus or (system.logical_cpus if allow_smt else (system.physical_cores or system.logical_cpus))
        total = max_cpus or n * rpn
        mem = memory_per_node if memory_per_node is not None else qmem
        return ResourceEnvelope(
            nodes=n, max_total_ranks=total, max_ranks_per_node=rpn,
            memory_per_node_gib=mem,
            source=f"PBS queue {queue}" if queue and qcpus else "PBS user overrides/local fallback",
            physical_cores_per_node=None,
            logical_cpus_per_node=qcpus,
        )
