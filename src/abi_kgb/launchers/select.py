from __future__ import annotations

from ..models import LauncherPlan, MpiInfo, SchedulerInfo


def select_launcher(mpi: MpiInfo, scheduler: SchedulerInfo, explicit: str = "auto") -> LauncherPlan:
    """Select a conservative launcher template.

    The template contains ``{ranks}`` and is later completed with ABINIT and
    input arguments by the script writer. Site-specific overrides remain
    available because MPI/scheduler integration is not globally uniform.
    """
    exp = explicit.lower()
    if exp not in {"auto", "mpiexec", "mpirun", "srun"}:
        raise ValueError("launcher must be auto, mpiexec, mpirun, or srun")

    if exp == "srun":
        return LauncherPlan("srun", "srun -n {ranks}", "Explicit direct SLURM launcher")
    if exp in {"mpiexec", "mpirun"}:
        return LauncherPlan(exp, f"{exp} -np {{ranks}}", "Explicit MPI launcher")

    path = mpi.launcher_path or "mpiexec"
    name = mpi.launcher_name or "mpiexec"

    if scheduler.kind == "local":
        return LauncherPlan(name, f'"{path}" -np {{ranks}}', f"Local {mpi.family or 'MPI'} launcher")

    if scheduler.kind == "slurm":
        if mpi.family == "mpich" and "slurm" in mpi.hydra_launchers:
            return LauncherPlan(
                name,
                f'"{path}" -np {{ranks}}',
                "MPICH/Hydra reports a Slurm bootstrap launcher; mpiexec can launch inside the allocation.",
            )
        if mpi.family == "openmpi":
            return LauncherPlan(
                name,
                f'"{path}" -np {{ranks}}',
                "Open MPI launcher inside a Slurm allocation. Use --launcher srun only when site PMIx guidance requires it.",
            )
        if mpi.family in {"intelmpi", "mvapich"}:
            return LauncherPlan(name, f'"{path}" -np {{ranks}}', f"{mpi.family} launcher inside Slurm allocation")
        if mpi.family == "cray-mpich":
            return LauncherPlan(
                "srun",
                "srun -n {ranks}",
                "Cray MPICH detected; srun is the conservative Slurm-native choice.",
                ("Verify site documentation because some Cray systems use additional CPU/GPU binding flags.",),
            )
        return LauncherPlan(
            name,
            f'"{path}" -np {{ranks}}',
            "Generic MPI launcher inside Slurm allocation",
            ("MPI/Slurm integration could not be identified; verify the launcher against site documentation.",),
        )

    # PBS family
    if mpi.family == "mpich":
        if "pbs" in mpi.hydra_launchers:
            return LauncherPlan(
                name,
                f'"{path}" -launcher pbs -np {{ranks}}',
                "MPICH/Hydra reports PBS bootstrap support.",
            )
        return LauncherPlan(
            name,
            f'"{path}" -np {{ranks}} -f "$PBS_NODEFILE"',
            "MPICH fallback using PBS_NODEFILE.",
            ("If your MPICH was built with PBS/TM support, the -f option may be unnecessary.",),
        )
    if mpi.family == "openmpi":
        return LauncherPlan(
            name,
            f'"{path}" -np {{ranks}}',
            "Open MPI generally discovers PBS allocations through TM/PBS integration.",
            ("If host discovery fails, retry with --hostfile \"$PBS_NODEFILE\" according to site policy.",),
        )
    if mpi.family == "intelmpi":
        return LauncherPlan(
            name,
            f'"{path}" -np {{ranks}} -hostfile "$PBS_NODEFILE"',
            "Intel MPI PBS-nodefile launcher.",
        )
    return LauncherPlan(
        name,
        f'"{path}" -np {{ranks}}',
        "Generic MPI launcher under PBS.",
        ("MPI/PBS integration could not be identified; verify whether PBS_NODEFILE or TM is required.",),
    )
