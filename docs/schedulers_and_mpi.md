# Scheduler and MPI portability

No single MPI command is universally correct on every HPC installation. Abi_KGB therefore detects **two independent layers**:

1. scheduler/resource manager (local, SLURM, PBS family), and
2. MPI implementation/launcher (MPICH/Hydra, Open MPI, Intel MPI, Cray MPICH, MVAPICH, unknown).

## Local

Abi_KGB uses `mpiexec` or `mpirun` from `PATH`, defaults to physical cores, and generates a local shell runner. It prints the `nohup` command rather than embedding `nohup` inside the runner.

## SLURM

Inside an allocation, resources are derived from `SLURM_NNODES`, `SLURM_NTASKS`, `SLURM_CPUS_ON_NODE`, and memory variables when present. Outside an allocation, `--partition` permits a best-effort `sinfo` query, but a live ABINIT probe is intentionally not launched on the login host.

MPICH/Hydra is launched through `mpiexec` when Hydra reports `slurm` bootstrap support. Open MPI defaults to `mpirun/mpiexec` inside the allocation. Cray MPICH conservatively prefers `srun`. Use `--launcher` to override site-specific policy.

## PBS family

Inside a PBS allocation, repeated host entries in `PBS_NODEFILE` are counted as allocated MPI slots. `qstat -f` is queried for memory where available.

- MPICH/Hydra with PBS launcher support: `mpiexec -launcher pbs`.
- MPICH without detected PBS bootstrap: PBS nodefile fallback.
- Open MPI: `mpirun/mpiexec` with its usual PBS/TM integration; a warning suggests a hostfile if discovery fails.
- Intel MPI: nodefile-based hostfile launch.
- Torque is detected separately for `nodes=N:ppn=M` script syntax.

These are conservative defaults, not a substitute for site documentation. Abi_KGB always reports a warning when integration cannot be identified.
