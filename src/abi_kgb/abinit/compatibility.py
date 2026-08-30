from __future__ import annotations

from ..models import AbiInputInfo


def assess_kgb_compatibility(info: AbiInputInfo) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    # ABINIT paral_kgb is the ground-state/NSCF wavefunction distribution.
    if info.optdriver != 0:
        reasons.append(
            f"optdriver={info.optdriver}: Abi_KGB v1.0 only advises paral_kgb for ground-state/NSCF inputs (optdriver=0)."
        )
    if info.ndtset != 1:
        reasons.append(
            f"ndtset={info.ndtset}: v1.0 refuses to rewrite multi-dataset inputs because datasets may require different layouts."
        )
    if info.nspinor not in (1, 2):
        reasons.append(f"unexpected nspinor={info.nspinor}; automatic KGB advice is disabled")
    return (not reasons), reasons
