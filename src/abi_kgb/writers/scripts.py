from __future__ import annotations

import math
import shlex
from pathlib import Path

from ..models import Candidate, LauncherPlan, SchedulerInfo


def _module_lines(modules: list[str]) -> list[str]:
    if not modules:
        return []
    lines = ["# Reproduce requested module environment", "module purge"]
    lines.extend(f"module load {shlex.quote(x)}" for x in modules)
    return lines + [""]


def write_run_script(
    path: Path,
    *,
    input_path: Path,
    candidate: Candidate,
    scheduler: SchedulerInfo,
    launcher: LauncherPlan,
    nodes: int,
    ranks_per_node: int | None,
    abinit: str,
    partition: str | None = None,
    queue: str | None = None,
    walltime: str | None = None,
    job_name: str | None = None,
    modules: list[str] | None = None,
    pbs_flavor: str | None = None,
) -> None:
    modules = modules or []
    rpn = ranks_per_node or math.ceil(candidate.mpi / nodes)
    job = job_name or input_path.stem[:64]
    lines: list[str] = ["#!/usr/bin/env bash", "set -euo pipefail"]

    if scheduler.kind == "slurm":
        lines += [
            f"#SBATCH --job-name={job}",
            f"#SBATCH --nodes={nodes}",
            f"#SBATCH --ntasks={candidate.mpi}",
            f"#SBATCH --ntasks-per-node={rpn}",
        ]
        if partition:
            lines.append(f"#SBATCH --partition={partition}")
        if walltime:
            lines.append(f"#SBATCH --time={walltime}")
        lines += ["", 'cd "${SLURM_SUBMIT_DIR:-$PWD}"', ""]
    elif scheduler.kind == "pbs":
        lines += [f"#PBS -N {job}"]
        if queue:
            lines.append(f"#PBS -q {queue}")
        if (pbs_flavor or "").lower() == "torque":
            lines.append(f"#PBS -l nodes={nodes}:ppn={rpn}")
        else:
            lines.append(f"#PBS -l select={nodes}:ncpus={rpn}:mpiprocs={rpn}")
        if walltime:
            lines.append(f"#PBS -l walltime={walltime}")
        lines += ["", 'cd "${PBS_O_WORKDIR:-$PWD}"', ""]

    lines += _module_lines(modules)
    lines += [
        "export OMP_NUM_THREADS=1",
        "export OPENBLAS_NUM_THREADS=1",
        "export MKL_NUM_THREADS=1",
        "export BLIS_NUM_THREADS=1",
        "",
    ]
    cmd_prefix = launcher.command_template.format(ranks=candidate.mpi)
    qabi = shlex.quote(abinit)
    qinp = shlex.quote(str(input_path))
    log = shlex.quote(input_path.stem + ".log")
    err = shlex.quote(input_path.stem + ".err")
    lines += [
        f"{cmd_prefix} {qabi} {qinp} > {log} 2> {err}",
    ]
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o755)


def local_nohup_command(script: Path) -> str:
    return f"nohup ./{script.name} > {script.stem}.master.log 2>&1 &"
