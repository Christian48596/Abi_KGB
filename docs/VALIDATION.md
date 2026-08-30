# Validation strategy

Abi_KGB separates deterministic unit tests from environment-dependent integration tests.

## Automated tests

The repository test suite validates:

- scalar ABINIT input parsing and KGB-block replacement,
- parsing of an ABINIT-style autoparal table whose best candidate is 112 MPI ranks with a 28/2/2 KGB split,
- empirical memory ranking and OOM rejection,
- local physical-core defaults,
- active SLURM resource extraction,
- PBS nodefile slot counting,
- MPICH/Hydra launcher selection for SLURM and PBS,
- Cray-MPICH Slurm fallback,
- local/SLURM/PBS script writers, and
- an offline end-to-end CLI invocation using a sanitized autoparal fixture.

Run:

```bash
python3 run_tests.py
```

## Environment-dependent validation

Real ABINIT/MPI integration cannot be fully reproduced in generic CI because it depends on an installed ABINIT build, pseudopotentials, scheduler plugins, and site configuration. For new environments, maintainers should record sanitized evidence from:

```bash
abi-kgb doctor
abi-kgb calculation.abi --autoparal-log autoparal.log
```

and, when permitted inside a compute allocation, compare the live one-rank autoparal result with the recommendation.

## Memory claims

Memory safety is validated only when a user supplies measured RSS calibration. The automated suite checks classification logic but does not claim that a generic formula predicts ABINIT peak memory for all calculations.
