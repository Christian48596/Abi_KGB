# Changelog

All notable changes to Abi_KGB are documented here.

## 1.0.0 - 2026-08-30

### Added

- modular hardware, ABINIT, MPI, scheduler, optimizer, and writer layers,
- Linux/WSL CPU, NUMA, memory and cgroup detection,
- local, SLURM, PBS Pro/OpenPBS and best-effort Torque resource backends,
- MPICH/Hydra, Open MPI, Intel MPI, Cray MPICH and MVAPICH identification,
- scheduler-aware launcher planning,
- one-rank ABINIT autoparal probing with optional fixed `npfft`,
- conservative algebraic fallback,
- empirical per-node RSS calibration and explicit OK/TIGHT/REJECT/UNKNOWN verdicts,
- patched `.abi` and local/SLURM/PBS script generation,
- `abi-kgb doctor`, JSON reports, tests, CI, documentation, citation metadata.

### Scope

- single-dataset `optdriver=0` KGB workflows only,
- CPU KGB advice; GPU-specific optimization is deferred.
