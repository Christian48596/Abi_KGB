from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .detection import detect_abinit, detect_mpi, detect_system
from .launchers import select_launcher
from .schedulers import detect_scheduler, resource_envelope


def doctor_report(*, scheduler="auto", partition=None, queue=None, abinit=None, mpi_launcher=None,
                  launcher="auto") -> dict:
    system = detect_system()
    mpi = detect_mpi(mpi_launcher)
    abi = detect_abinit(abinit)
    backend, sched = detect_scheduler(scheduler, partition=partition, queue=queue)
    resources = resource_envelope(backend, system, partition_or_queue=partition or queue)
    plan = select_launcher(mpi, sched, launcher) if mpi.family != "none" else None
    return {
        "system": dataclasses.asdict(system),
        "mpi": dataclasses.asdict(mpi),
        "abinit": dataclasses.asdict(abi),
        "scheduler": dataclasses.asdict(sched),
        "resources": dataclasses.asdict(resources),
        "launcher_plan": dataclasses.asdict(plan) if plan else None,
    }


def print_doctor(report: dict) -> None:
    s = report["system"]; m = report["mpi"]; a = report["abinit"]; q = report["scheduler"]; r = report["resources"]
    print("Abi_KGB doctor")
    print("=" * 64)
    print(f"Host                 : {s['hostname']}{' (WSL)' if s['is_wsl'] else ''}")
    print(f"OS / kernel          : {s['os_name']} / {s['kernel']}")
    print(f"CPU                  : {s['cpu_model'] or '?'}")
    print(f"Physical/logical CPU : {s['physical_cores'] or '?'} / {s['logical_cpus']}")
    print(f"NUMA nodes           : {s['numa_nodes'] or '?'}")
    print(f"RAM available/limit  : {s['mem_available_gib']:.2f} / {s['mem_effective_limit_gib']:.2f} GiB")
    print(f"GPUs detected        : {len(s['gpus'])}")
    print(f"Scheduler            : {q['kind']}{' (active allocation)' if q['active_allocation'] else ''}")
    print(f"Resources            : {r['nodes']} node(s), <= {r['max_total_ranks']} ranks, <= {r['max_ranks_per_node']}/node")
    print(f"Memory/node          : {r['memory_per_node_gib'] if r['memory_per_node_gib'] is not None else '?'} GiB")
    print(f"MPI                  : {m['family']} | {m['launcher_path'] or 'NOT FOUND'}")
    print(f"ABINIT               : {a['version'] or '?'} | {a['executable'] or 'NOT FOUND'}")
    lp = report.get("launcher_plan")
    if lp:
        print(f"Launcher plan        : {lp['command_template']}")
        print(f"Launcher rationale   : {lp['explanation']}")
        for warning in lp.get("warnings", []):
            print(f"WARNING              : {warning}")
