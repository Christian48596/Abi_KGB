# Limitations

Abi_KGB v1.0.0 deliberately has a narrow, defensible scope.

## Supported

- ABINIT `paral_kgb` ground-state/NSCF workflows (`optdriver=0`).
- single-dataset inputs.
- Linux and WSL hardware discovery.
- local, SLURM, PBS Pro/OpenPBS, and best-effort Torque script generation.
- common MPICH, Open MPI, Intel MPI, Cray MPICH, and MVAPICH identification.
- ABINIT `autoparal` candidate parsing.
- empirical peak-RSS calibration.

## Not claimed

- universal site-policy discovery: partitions/queues and module policies can be administrative choices rather than detectable hardware facts.
- a proof against OOM.
- GPU-optimized KGB recommendations.
- DFPT, GW, BSE, EPH, or other non-KGB ABINIT drivers.
- automatic rewriting of multi-dataset ABINIT inputs.
- performance prediction without benchmarks; ABINIT's weight is a heuristic rather than a measured wall time.
- Windows-native execution without WSL.

When Abi_KGB cannot establish a requirement, it should warn or refuse rather than silently guess.
