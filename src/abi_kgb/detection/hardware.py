from __future__ import annotations

import os
import platform
from pathlib import Path

from ..models import SystemInfo
from ..util import run_capture


def _meminfo() -> tuple[float, float]:
    total = avail = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total = float(line.split()[1]) / 1024 / 1024
            elif line.startswith("MemAvailable:"):
                avail = float(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    if total is None:
        total = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3
    if avail is None:
        avail = total
    return total, avail


def _cgroup_memory_gib() -> tuple[float | None, float | None]:
    """Return (limit GiB, current GiB) for cgroup v2/v1 when constrained."""
    pairs = [
        (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory.current")),
        (Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"), Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")),
    ]
    for limit_path, current_path in pairs:
        try:
            raw = limit_path.read_text().strip()
        except OSError:
            continue
        if raw == "max":
            continue
        try:
            limit = int(raw)
        except ValueError:
            continue
        if limit <= 0 or limit >= 2**60:
            continue
        current = None
        try:
            current = int(current_path.read_text().strip())
        except (OSError, ValueError):
            pass
        return limit / 1024**3, (current / 1024**3 if current is not None else None)
    return None, None


def _lscpu_values() -> dict[str, str]:
    vals: dict[str, str] = {}
    for line in run_capture(["lscpu"]).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            vals[k.strip()] = v.strip()
    return vals


def _int_field(vals: dict[str, str], key: str) -> int | None:
    try:
        return int(vals.get(key, ""))
    except ValueError:
        return None


def _affinity_topology() -> tuple[int | None, int | None]:
    """Return (logical CPUs in affinity, unique physical cores in affinity)."""
    try:
        cpus = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return None, None
    cores: set[tuple[str, str]] = set()
    for cpu in cpus:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            core = (base / "core_id").read_text().strip()
            pkg = (base / "physical_package_id").read_text().strip()
            cores.add((pkg, core))
        except OSError:
            pass
    return len(cpus), (len(cores) if cores else None)


def _gpus() -> tuple[str, ...]:
    out = run_capture(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], timeout=5)
    return tuple(x.strip() for x in out.splitlines() if x.strip())


def detect_system() -> SystemInfo:
    vals = _lscpu_values()
    affinity_logical, affinity_physical = _affinity_topology()
    logical = affinity_logical or os.cpu_count() or _int_field(vals, "CPU(s)") or 1
    sockets = _int_field(vals, "Socket(s)")
    cps = _int_field(vals, "Core(s) per socket")
    physical = affinity_physical or (sockets * cps if sockets and cps else None)
    tpc = _int_field(vals, "Thread(s) per core")
    numa = _int_field(vals, "NUMA node(s)")
    total, avail = _meminfo()
    cg_limit, cg_current = _cgroup_memory_gib()
    effective = min(total, cg_limit) if cg_limit is not None else total
    if cg_limit is not None and cg_current is not None:
        avail = min(avail, max(0.0, cg_limit - cg_current))
    try:
        version = Path("/proc/version").read_text().lower()
    except OSError:
        version = ""
    is_wsl = "microsoft" in version or "wsl" in version
    return SystemInfo(
        hostname=platform.node(),
        os_name=platform.system(),
        kernel=platform.release(),
        is_wsl=is_wsl,
        cpu_model=vals.get("Model name"),
        logical_cpus=logical,
        physical_cores=physical,
        sockets=sockets,
        threads_per_core=tpc,
        numa_nodes=numa,
        mem_total_gib=total,
        mem_available_gib=min(avail, effective),
        mem_effective_limit_gib=effective,
        gpus=_gpus(),
    )
