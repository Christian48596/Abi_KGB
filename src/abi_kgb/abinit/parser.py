from __future__ import annotations

import re
from pathlib import Path

from ..models import AbiInputInfo, Candidate

SCALAR_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s+|=\s*)([^#!\n]+)")
KGB_KEYS = {"autoparal", "max_ncpus", "paral_kgb", "np_spkpt", "npband", "npfft", "bandpp", "npspinor"}


def strip_comment(line: str) -> str:
    # ABINIT accepts comments introduced by # and ! in ordinary input lines.
    for mark in ("#", "!"):
        if mark in line:
            line = line.split(mark, 1)[0]
    return line.strip()


def _first_num(text: str, integer: bool = False):
    token = text.strip().split()[0].replace("D", "E").replace("d", "e")
    try:
        return int(float(token)) if integer else float(token)
    except ValueError:
        return None


def parse_abi(path: Path) -> AbiInputInfo:
    text = path.read_text(errors="replace")
    values: dict[str, str] = {}
    manual = False
    autoparal = False
    for raw in text.splitlines():
        line = strip_comment(raw)
        if not line:
            continue
        m = SCALAR_RE.match(line)
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        # Keep unsuffixed/global variables. Dataset-specific inputs are detected
        # through ndtset and treated conservatively by compatibility checks.
        values[key] = val
        if key in KGB_KEYS - {"autoparal", "max_ncpus"}:
            manual = True
        if key == "autoparal":
            autoparal = (_first_num(val, True) or 0) != 0

    def iv(name: str, default=None):
        return _first_num(values[name], True) if name in values else default

    def fv(name: str, default=None):
        return _first_num(values[name], False) if name in values else default

    ndtset = iv("ndtset", 1) or 1
    pawecut = fv("pawecutdg")
    # pawecutdg is a strong input-level signal for PAW, although this remains
    # a heuristic because ABINIT ultimately determines pseudopotential type.
    likely_paw = pawecut is not None
    return AbiInputInfo(
        path=path,
        ndtset=ndtset,
        nband=iv("nband"),
        nkpt=iv("nkpt"),
        nsppol=iv("nsppol", 1) or 1,
        nspinor=iv("nspinor", 1) or 1,
        npspinor=iv("npspinor", 1) or 1,
        natom=iv("natom"),
        ecut_ha=fv("ecut"),
        pawecutdg_ha=pawecut,
        optdriver=iv("optdriver", 0) or 0,
        iscf=iv("iscf"),
        has_manual_kgb=manual,
        has_autoparal=autoparal,
        likely_paw=likely_paw,
        raw_values=values,
    )


def remove_global_kgb_lines(text: str) -> tuple[str, list[str]]:
    kept: list[str] = []
    removed: list[str] = []
    for raw in text.splitlines():
        line = strip_comment(raw)
        m = SCALAR_RE.match(line) if line else None
        if m and m.group(1).lower() in KGB_KEYS:
            removed.append(raw)
        else:
            kept.append(raw)
    return "\n".join(kept).rstrip() + "\n", removed


def patch_kgb_block(inp: Path, out: Path, candidate: Candidate) -> list[str]:
    clean, removed = remove_global_kgb_lines(inp.read_text(errors="replace"))
    block = (
        "\n# --- Abi_KGB v1.0.0 recommended KGB parallelization ---\n"
        "paral_kgb 1\n"
        f"np_spkpt {candidate.np_spkpt}\n"
        f"npband {candidate.npband}\n"
        f"npfft {candidate.npfft}\n"
        f"bandpp {candidate.bandpp}\n"
        + (f"npspinor {candidate.npspinor}\n" if candidate.npspinor != 1 else "")
        + "# --- end Abi_KGB block ---\n"
    )
    out.write_text(clean + block)
    return removed
