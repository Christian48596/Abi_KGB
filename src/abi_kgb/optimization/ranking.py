from __future__ import annotations

import math

from ..models import AbiInputInfo, Calibration, Candidate, RankedCandidate, ResourceEnvelope, SystemInfo
from .memory import fit_memory


def divisors(n: int) -> list[int]:
    if n <= 0:
        return []
    vals: list[int] = []
    for i in range(1, int(math.sqrt(n)) + 1):
        if n % i == 0:
            vals.append(i)
            if i * i != n:
                vals.append(n // i)
    return sorted(vals)


def static_candidates(info: AbiInputInfo, max_cpus: int, *, npfft_max: int = 8) -> list[Candidate]:
    """Algebraic fallback when ABINIT autoparal cannot be run.

    This deliberately refuses to infer ``nkpt`` from ``ngkpt`` because the
    irreducible k-point count depends on symmetry and ABINIT settings. The live
    ABINIT autoparal probe is therefore preferred.
    """
    if not info.nband or not info.spin_k:
        return []
    out: list[Candidate] = []
    for sp in divisors(info.spin_k):
        for nb in divisors(info.nband):
            for ff in range(1, npfft_max + 1):
                mpi = sp * nb * ff * info.npspinor
                if mpi > max_cpus:
                    continue
                denom = info.nband // nb
                bandpps = [1] + [x for x in divisors(denom) if x % 2 == 0]
                for bpp in sorted(set(bandpps), reverse=True):
                    # Synthetic ordering only; source label makes this explicit.
                    weight = 10.0 * math.log2(sp + 1) + 4.0 * math.log2(nb + 1) - 1.5 * (ff - 1)
                    out.append(Candidate(sp, ff, nb, bpp, mpi, weight, npspinor=info.npspinor, source="static"))
    return sorted(out, key=lambda c: (c.weight, c.mpi), reverse=True)


def rank_candidates(
    candidates: list[Candidate],
    *,
    system: SystemInfo,
    resources: ResourceEnvelope,
    reserve_fraction: float,
    npfft_max: int | None,
    calibrations: list[Calibration],
    prefer_physical: bool = True,
) -> list[RankedCandidate]:
    if not candidates:
        return []
    max_weight = max(c.weight for c in candidates) or 1.0
    budget = None
    if resources.memory_per_node_gib is not None:
        budget = resources.memory_per_node_gib * (1.0 - reserve_fraction)
    ranked: list[RankedCandidate] = []
    for c in candidates:
        if c.mpi > resources.max_total_ranks:
            continue
        if npfft_max is not None and c.npfft > npfft_max:
            continue
        rpn = math.ceil(c.mpi / resources.nodes)
        if rpn > resources.max_ranks_per_node:
            continue
        score = 100.0 * c.weight / max_weight
        score += 8.0 * min(1.0, c.mpi / resources.max_total_ranks)
        notes: list[str] = []
        if resources.nodes > 1 and c.mpi % resources.nodes:
            score -= 2.0
            notes.append("MPI ranks do not divide evenly across requested nodes")
        if resources.nodes == 1 and prefer_physical and system.physical_cores and c.mpi > system.physical_cores:
            score -= 8.0
            notes.append("uses SMT/hardware threads beyond physical cores")
        if c.bandpp >= 32 and not calibrations:
            notes.append("large bandpp with uncalibrated memory; monitor RSS")
        elif c.bandpp > 1 and calibrations:
            score -= min(4.0, math.log2(c.bandpp) * 0.35)
        est = fit_memory(calibrations, rpn)
        if est is None or budget is None:
            status = "UNKNOWN"
        elif est > budget:
            status = "REJECT"
            score -= 1000
            notes.append(f"estimated {est:.1f} GiB/node exceeds {budget:.1f} GiB/node safety budget")
        elif est > 0.85 * budget:
            status = "TIGHT"
            score -= 12
            notes.append("estimated RSS is close to the configured safety budget")
        else:
            status = "OK"
            score += 3
        ranked.append(RankedCandidate(c, score, est, status, notes))
    return sorted(ranked, key=lambda r: r.score, reverse=True)
