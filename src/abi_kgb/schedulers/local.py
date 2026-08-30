from __future__ import annotations

from ..models import ResourceEnvelope, SchedulerInfo, SystemInfo
from .base import SchedulerBackend


class LocalBackend(SchedulerBackend):
    kind = "local"

    def info(self) -> SchedulerInfo:
        return SchedulerInfo(kind="local", active_allocation=False)

    def resources(self, system: SystemInfo, *, nodes=None, max_cpus=None,
                  ranks_per_node=None, memory_per_node=None,
                  partition_or_queue=None, allow_smt=False) -> ResourceEnvelope:
        if nodes not in (None, 1):
            raise ValueError("local backend supports exactly one node")
        default_ranks = system.logical_cpus if allow_smt else (system.physical_cores or system.logical_cpus)
        cap = max_cpus or default_ranks
        rpn = ranks_per_node or cap
        mem = memory_per_node if memory_per_node is not None else system.mem_available_gib
        return ResourceEnvelope(
            nodes=1,
            max_total_ranks=cap,
            max_ranks_per_node=rpn,
            memory_per_node_gib=mem,
            source="local hardware/cgroup limits",
            physical_cores_per_node=system.physical_cores,
            logical_cpus_per_node=system.logical_cpus,
        )
