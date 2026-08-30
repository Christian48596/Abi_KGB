<p align="center">
  <img src="assets/Abi_KGB_logo.png"
       alt="Abi_KGB logo"
       width="300">
</p>

<h1 align="center">Abi_KGB</h1>

<p align="center">
  Hardware-aware KGB parallelization advisor for ABINIT
</p>


[![tests](https://github.com/Christian48596/Abi_KGB/actions/workflows/tests.yml/badge.svg)](https://github.com/Christian48596/Abi_KGB/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**Abi_KGB** is a portable, hardware-aware advisor for ABINIT's ground-state KGB MPI parallelization (`paral_kgb`). Give it an ABINIT `*.abi` input and it will:

1. inspect the computer visible to the process (CPU topology, NUMA, RAM/cgroup/WSL limit, optional GPUs),
2. detect local, SLURM, or PBS-family execution,
3. identify the MPI implementation and a conservative launch strategy,
4. inspect the ABINIT input and refuse unsupported KGB cases,
5. ask ABINIT itself for legal `autoparal` configurations whenever a live compute context is available,
6. rank `np_spkpt`, `npband`, `npfft`, and `bandpp` layouts against the available resources,
7. incorporate measured peak RSS data when supplied so memory-risk decisions are empirical rather than invented, and
8. write a patched `.abi` plus a ready-to-run local, SLURM, or PBS script.

Abi_KGB is intentionally a **thin advisor around ABINIT**, not a replacement for ABINIT or a general workflow engine.

## Scope

Version 1.0.0 supports CPU-side KGB advice for **single-dataset ABINIT ground-state/NSCF inputs** (`optdriver=0`). ABINIT documents `paral_kgb` as a wavefunction distribution for ground-state calculations; DFPT, GW, BSE, EPH, and other drivers use different parallelization models and are therefore rejected rather than guessed.

GPU-specific KGB optimization is not yet claimed by v1.0.0. ABINIT's GPU path has different parallel behavior (notably `npfft` is not used in the same way), so Abi_KGB reports detected GPUs but keeps CPU recommendations separate.

## Repository layout

The Python package uses the standard `src` layout: implementation code lives in `src/abi_kgb/`, tests in `tests/`, examples in `examples/`, and technical documentation in `docs/`.

## Installation

Abi_KGB has no runtime Python dependencies outside the standard library.

```bash
python3 -m pip install .
```

For development:

```bash
git clone https://github.com/Christian48596/Abi_KGB.git
cd Abi_KGB
python3 -m pip install -e .
```

Without installation:

```bash
python3 -m abi_kgb calculation.abi
```

Requirements:

- Python >= 3.10
- ABINIT available in `PATH` (or pass `--abinit`)
- an MPI launcher for live probes (`mpiexec`/`mpirun`, or scheduler-native launch where selected)
- Linux/WSL for full hardware discovery; other Unix-like systems receive best-effort discovery

## 30-second usage

First diagnose the environment:

```bash
abi-kgb doctor
```

Then advise an input:

```bash
abi-kgb calculation.abi
```

If FFT parallelism is known to be unstable on a particular ABINIT build:

```bash
abi-kgb calculation.abi --npfft-fixed 1
```

To generate files:

```bash
abi-kgb calculation.abi --npfft-fixed 1 --write
```

On a workstation this writes `calculation.kgb.abi` and `run_kgb.sh`, and prints a background command such as:

```bash
nohup ./run_kgb.sh > run_kgb.master.log 2>&1 &
```

On SLURM it writes `run_kgb.slurm` and prints:

```bash
sbatch run_kgb.slurm
```

On PBS/OpenPBS/PBS Pro it writes `run_kgb.pbs` and prints:

```bash
qsub run_kgb.pbs
```

## Scheduler detection

Abi_KGB distinguishes scheduler detection from KGB optimization.

### Local / workstation / WSL

```bash
abi-kgb calculation.abi --scheduler local
```

The default MPI-rank ceiling is the number of **physical cores**, not SMT threads. Use `--allow-smt` only when benchmarking shows a benefit.

### SLURM

Inside an active allocation, Abi_KGB reads the SLURM environment and uses the allocated task/node limits.

```bash
salloc -N 2 -n 112 -p cpu
abi-kgb calculation.abi --npfft-fixed 1 --write
```

Outside an allocation, request the scheduler/partition explicitly:

```bash
abi-kgb calculation.abi --scheduler slurm --partition cpu --nodes 2 --max-cpus 112
```

Abi_KGB will **not launch the live ABINIT autoparal probe on a detected login node**. Supply an existing autoparal log or enter a compute allocation.

### PBS / OpenPBS / PBS Professional / Torque

Inside a PBS allocation, Abi_KGB uses `PBS_JOBID`, `PBS_NODEFILE`, `PBS_QUEUE`, and `PBS_O_WORKDIR` when available.

```bash
abi-kgb calculation.abi --scheduler pbs --write
```

Outside an allocation:

```bash
abi-kgb calculation.abi --scheduler pbs --queue workq --nodes 2 --max-cpus 112
```

PBS sites differ in MPI/TM integration. Abi_KGB detects common MPICH/Open MPI/Intel MPI cases and emits warnings when the launcher cannot be identified reliably.

## ABINIT autoparal is the authority for legality

Abi_KGB prefers a one-rank ABINIT probe using:

```text
autoparal 1
max_ncpus N
```

and parses ABINIT's own candidate table. This is deliberate: FFT-grid constraints and internal heuristics are calculation dependent. If `--npfft-fixed 1` is supplied, Abi_KGB fixes `npfft` in the temporary probe and lets ABINIT optimize the other KGB levels around that restriction.

An existing log can be used without running ABINIT:

```bash
abi-kgb calculation.abi --autoparal-log autoparal.log
```

A purely algebraic fallback exists:

```bash
abi-kgb calculation.abi --no-autoparal
```

but it is used only when global `nkpt` and `nband` are explicit and is clearly labeled as a fallback.

## Memory/OOM model

Abi_KGB does **not** promise that a decomposition cannot OOM. ABINIT itself notes that startup memory estimates can be lower than peak use because workspace arrays are not all represented. Without empirical measurements, Abi_KGB reports memory status as `UNKNOWN`.

With measured data:

```bash
abi-kgb calculation.abi \
  --calibration 7:8.0 \
  --calibration 20:14.0 \
  --npfft-fixed 1
```

Here `20:14.0` means 20 ranks per node produced 14 GiB peak ABINIT RSS on that node.

The monitor logs used by the FePS3 case can be consumed directly:

```bash
abi-kgb calculation.abi \
  --memory-log calculation.memory.log \
  --memory-log-ranks 20
```

Memory verdicts are:

- `OK`: empirical estimate below the configured safety region,
- `TIGHT`: close to the memory budget,
- `REJECT`: empirical estimate exceeds the budget,
- `UNKNOWN`: insufficient evidence for a memory claim.

The default reserve is 20% and can be changed with `--reserve`.

## Important options

```text
--scheduler auto|local|slurm|pbs
--partition NAME
--queue NAME
--nodes N
--max-cpus N
--ranks-per-node N
--memory-per-node GiB
--allow-smt
--npfft-fixed N
--npfft-max N
--autoparal-log FILE
--no-autoparal
--calibration RANKS:RSS_GiB
--memory-log FILE
--memory-log-ranks N
--launcher auto|mpiexec|mpirun|srun
--module NAME
--walltime HH:MM:SS
--write
--json report.json
```

## Why not simply use AbiPy?

AbiPy already provides a rich ABINIT workflow stack, including TaskManager/autoparal facilities and scheduler adapters. Abi_KGB has a deliberately narrower purpose. It operates directly on an existing `.abi`, requires no scientific Python stack or manager configuration, discovers the current machine/scheduler/MPI environment, provides explicit empirical RSS/OOM reasoning, and generates a small stand-alone launch script. Users already committed to AbiPy's workflow model may prefer AbiPy; Abi_KGB targets direct ABINIT users and heterogeneous machines where a lightweight diagnostic/advice tool is useful.

## Tests

Run the standard-library test suite:

```bash
python3 run_tests.py
```

or:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers ABINIT input parsing, real-shape autoparal tables, memory ranking, WSL/local resource logic, SLURM allocation parsing, PBS nodefiles, MPI launcher selection, script generation, and an offline end-to-end CLI test.

GitHub Actions runs the suite on Python 3.10-3.13.

## Documentation

- [Architecture](docs/architecture.md)
- [Scheduler and MPI portability](docs/schedulers_and_mpi.md)
- [Memory safety model](docs/memory_model.md)
- [Limitations](docs/limitations.md)
- [Validation](docs/VALIDATION.md)
- [FePS3 case study](examples/FePS3_example.md)

## Contributing and support

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md). Use GitHub Issues for reproducible bugs and feature requests.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## License

MIT. See [LICENSE](LICENSE).
