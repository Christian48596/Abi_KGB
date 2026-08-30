# Memory model and OOM safety

Memory is a first-class constraint because increasing MPI ranks can replicate wavefunction, PAW, FFT, eigensolver, and communication workspaces. The direction and magnitude of the change are calculation/build dependent.

Abi_KGB therefore does **not** infer a precise peak RSS from `ecut`, `nband`, or atom count alone.

## Resource budget

For local systems, the memory budget is based on Linux-visible available memory and cgroup/WSL limits. On schedulers, allocated or explicitly requested per-node memory is preferred.

The ranking safety budget is:

```text
memory_per_node * (1 - reserve_fraction)
```

with a default 20% reserve.

## Empirical calibration

One or more measurements may be supplied:

```bash
--calibration 7:8.0 --calibration 20:14.0
```

The first number is ranks/node; the second is observed peak ABINIT RSS GiB/node.

With one point, larger rank counts are conservatively scaled in proportion to rank count. With two or more points, Abi_KGB fits a non-negative linear model `RSS = a + b*ranks`.

This is intentionally simple, inspectable, and explicitly labeled as an estimate.

## Verdicts

- `OK`: empirical estimate is below 85% of the usable budget.
- `TIGHT`: between 85% and 100% of the usable budget.
- `REJECT`: above the usable budget.
- `UNKNOWN`: no empirical estimate or no reliable memory budget.

`UNKNOWN` is not equivalent to safe.
