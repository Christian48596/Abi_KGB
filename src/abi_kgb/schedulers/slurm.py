from __future__ import annotations

import os
import re
import shutil

from ..models import ResourceEnvelope, SchedulerInfo, SystemInfo
from ..util import env_int, run_capture
from .base import SchedulerBackend


def _partition_resources(partition: str) -> tuple[int | None, float | None, int | None]:
    if not shutil.which("sinfo"):
        return None, None, None
    out = run_capture(["sinfo", "-h", "-p", partition, "-o", "%c|%m|%D"], timeout=10)
    rows: list[tuple[int, float, int]] = []
    for line in out.splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) != 3:
            continue
        try:
            cpus = int(re.search(r"\d+", parts[0]).group())
            mem_mb = int(re.search(r"\d+", parts[1]).group())
            n = int(re.search(r"\d+", parts[2]).group())
        except (AttributeError, ValueError):
            continue
        rows.append((cpus, mem_mb / 1024.0, n))
    if not rows:
        return None, None, None
    return min(x[0] for x in rows), min(x[1] for x in rows), sum(x[2] for x in rows)


class SlurmBackend(SchedulerBackend):
    kind = "slurm"

    def info(self) -> SchedulerInfo:
        active = "SLURM_JOB_ID" in os.environ
        return SchedulerInfo(
            kind="slurm",
            active_allocation=active,
            flavor="slurm",
            job_id=os.environ.get("SLURM_JOB_ID"),
            partition_or_queue=os.environ.get("SLURM_JOB_PARTITION"),
            submit_dir=os.environ.get("SLURM_SUBMIT_DIR"),
        )

    def resources(self, system: SystemInfo, *, nodes=None, max_cpus=None,
                  ranks_per_node=None, memory_per_node=None,
                  partition_or_queue=None, allow_smt=False) -> ResourceEnvelope:
        info = self.info()
        if info.active_allocation:
            n = nodes or env_int("SLURM_NNODES") or 1
            total = max_cpus or env_int("SLURM_NTASKS")
            cpus_on_node = env_int("SLURM_CPUS_ON_NODE")
            rpn = ranks_per_node or cpus_on_node
            if total is None and rpn:
                total = n * rpn
            if total is None:
                total = n * (system.physical_cores or system.logical_cpus)
            if rpn is None:
                rpn = max(1, total // n)
            mem = memory_per_node
            if mem is None:
                mem_mb = env_int("SLURM_MEM_PER_NODE")
                if mem_mb:
                    mem = mem_mb / 1024.0
                else:
                    mem_cpu_mb = env_int("SLURM_MEM_PER_CPU")
                    if mem_cpu_mb:
                        mem = mem_cpu_mb * rpn / 1024.0
            return ResourceEnvelope(
                nodes=n, max_total_ranks=total, max_ranks_per_node=rpn,
                memory_per_node_gib=mem,
                source="active SLURM allocation",
                physical_cores_per_node=None,
                logical_cpus_per_node=cpus_on_node,
            )
        part = partition_or_queue
        pcpus = pmem = None
        if part:
            pcpus, pmem, _ = _partition_resources(part)
        n = nodes or 1
        rpn = ranks_per_node or pcpus or (system.logical_cpus if allow_smt else (system.physical_cores or system.logical_cpus))
        total = max_cpus or n * rpn
        mem = memory_per_node if memory_per_node is not None else pmem
        return ResourceEnvelope(
            nodes=n, max_total_ranks=total, max_ranks_per_node=rpn,
            memory_per_node_gib=mem,
            source=f"SLURM partition {part}" if part and pcpus else "SLURM user overrides/local fallback",
            physical_cores_per_node=None,
            logical_cpus_per_node=pcpus,
        )
