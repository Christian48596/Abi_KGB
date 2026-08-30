from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ResourceEnvelope, SchedulerInfo, SystemInfo


class SchedulerBackend(ABC):
    kind: str

    @abstractmethod
    def info(self) -> SchedulerInfo:
        raise NotImplementedError

    @abstractmethod
    def resources(self, system: SystemInfo, *, nodes: int | None = None,
                  max_cpus: int | None = None, ranks_per_node: int | None = None,
                  memory_per_node: float | None = None,
                  partition_or_queue: str | None = None,
                  allow_smt: bool = False) -> ResourceEnvelope:
        raise NotImplementedError
