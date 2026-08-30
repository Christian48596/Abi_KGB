# FePS3 case study

Abi_KGB originated from a practical ABINIT parallelization problem for a monolayer FePS3 PAW PBEsol+U force check, followed by norm-conserving constrained-DFT work.

The ground-state input had, among other parameters:

```text
nband 240
nkpt 14
nsppol 2
```

so the calculation contained 28 spin-k components. On an HPC probe, ABINIT's own autoparal output favored a 112-rank `28 x 2 x 2` spin-k/FFT/band layout. On one ABINIT/MPICH environment, however, FFT parallelism above one had proven unstable in production, motivating the constrained probe mode:

```bash
abi-kgb FePS3_PBEsol_U_forcecheck.abi --npfft-fixed 1
```

On a WSL workstation with 20 physical cores, empirical RSS monitoring was then used to distinguish memory-safe and memory-risky rank counts. The intended workflow is:

```bash
abi-kgb doctor
abi-kgb FePS3_PBEsol_U_forcecheck.abi \
  --npfft-fixed 1 \
  --calibration 7:8.0 \
  --calibration 20:14.0 \
  --write
```

This case illustrates why Abi_KGB separates three questions that are often conflated:

1. which KGB decompositions ABINIT considers legal/efficient,
2. which resources the machine or scheduler actually provides, and
3. which MPI launch mechanism is appropriate for that site/build.

The numeric calibration values above are examples of the interface. Users should supply peak RSS measured for their own build and input when making memory-safety claims.
