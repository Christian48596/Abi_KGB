# Architecture

Abi_KGB v1.0.0 is intentionally layered so scheduler syntax cannot influence the scientific KGB ranking logic.

```text
*.abi
  |
  v
ABINIT parser + compatibility gate
  |
  +------> system detection (CPU/RAM/NUMA/WSL/cgroups)
  +------> scheduler backend (local / SLURM / PBS)
  +------> MPI detection + launcher selection
  |
  v
ABINIT one-rank autoparal probe
  |
  v
legal Candidate(np_spkpt, npfft, npband, bandpp, mpi, weight)
  |
  v
resource + empirical-memory ranking
  |
  v
patched .abi + local/SLURM/PBS runner
```

## Design principles

1. **ABINIT determines legal layouts whenever possible.** Abi_KGB parses `autoparal`; it does not attempt to reimplement ABINIT's internal FFT-grid rules.
2. **Schedulers are adapters.** They expose a normalized `ResourceEnvelope`; the optimizer does not know `#SBATCH`, `#PBS`, or nodefiles.
3. **MPI launch is separate from resource allocation.** A scheduler allocation and an MPI launcher are not the same thing.
4. **Unknown is better than false precision.** OOM safety is `UNKNOWN` unless there is empirical calibration or reliable node memory information.
5. **Unsupported ABINIT drivers are refused.** v1.0.0 does not translate KGB advice to DFPT/GW/BSE/EPH parallelization.

## Package layout

- `abi_kgb/abinit/`: input parsing, compatibility, autoparal parsing/probing.
- `abi_kgb/detection/`: hardware, MPI, and ABINIT discovery.
- `abi_kgb/schedulers/`: local, SLURM, PBS resource backends.
- `abi_kgb/launchers/`: MPI/scheduler launch strategy selection.
- `abi_kgb/optimization/`: memory model and candidate ranking.
- `abi_kgb/writers/`: patched input and launch-script generation.
