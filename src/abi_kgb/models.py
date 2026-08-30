from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SystemInfo:
    hostname: str
    os_name: str
    kernel: str
    is_wsl: bool
    cpu_model: Optional[str]
    logical_cpus: int
    physical_cores: Optional[int]
    sockets: Optional[int]
    threads_per_core: Optional[int]
    numa_nodes: Optional[int]
    mem_total_gib: float
    mem_available_gib: float
    mem_effective_limit_gib: float
    gpus: tuple[str, ...] = ()


@dataclass(frozen=True)
class MpiInfo:
    launcher_path: Optional[str]
    launcher_name: Optional[str]
    family: str
    version_line: Optional[str]
    hydra_launchers: tuple[str, ...] = ()
    slurm_mpi_plugins: tuple[str, ...] = ()


@dataclass(frozen=True)
class AbinitInfo:
    executable: Optional[str]
    version: Optional[str]
    build_text: str = ""
    mpi_enabled: Optional[bool] = None
    openmp_enabled: Optional[bool] = None
    gpu_enabled: Optional[bool] = None


@dataclass(frozen=True)
class SchedulerInfo:
    kind: str  # local, slurm, pbs
    active_allocation: bool
    flavor: Optional[str] = None
    job_id: Optional[str] = None
    partition_or_queue: Optional[str] = None
    submit_dir: Optional[str] = None
    nodefile: Optional[str] = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResourceEnvelope:
    nodes: int
    max_total_ranks: int
    max_ranks_per_node: int
    memory_per_node_gib: Optional[float]
    source: str
    physical_cores_per_node: Optional[int] = None
    logical_cpus_per_node: Optional[int] = None


@dataclass(frozen=True)
class AbiInputInfo:
    path: Path
    ndtset: int
    nband: Optional[int]
    nkpt: Optional[int]
    nsppol: int
    nspinor: int
    npspinor: int
    natom: Optional[int]
    ecut_ha: Optional[float]
    pawecutdg_ha: Optional[float]
    optdriver: int
    iscf: Optional[int]
    has_manual_kgb: bool
    has_autoparal: bool
    likely_paw: bool
    raw_values: dict[str, str] = field(default_factory=dict)

    @property
    def spin_k(self) -> Optional[int]:
        return self.nkpt * self.nsppol if self.nkpt is not None else None


@dataclass(frozen=True)
class Candidate:
    np_spkpt: int
    npfft: int
    npband: int
    bandpp: int
    mpi: int
    weight: float
    npspinor: int = 1
    source: str = "autoparal"


@dataclass(frozen=True)
class Calibration:
    ranks_per_node: int
    rss_gib_per_node: float


@dataclass
class RankedCandidate:
    candidate: Candidate
    score: float
    estimated_rss_per_node_gib: Optional[float]
    memory_status: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LauncherPlan:
    family: str
    command_template: str
    explanation: str
    warnings: tuple[str, ...] = ()
