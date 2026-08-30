from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from ..models import Candidate
from .parser import remove_global_kgb_lines

AUTO_ROW_RE = re.compile(
    r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*\|"
)


def parse_autoparal_text(text: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, int, int, int, int, float]] = set()
    for line in text.splitlines():
        m = AUTO_ROW_RE.search(line)
        if not m:
            continue
        sp, ff, nb, bpp, mpi, weight = m.groups()
        product = int(sp) * int(ff) * int(nb)
        ratio = int(mpi) // product if product and int(mpi) % product == 0 else 1
        npspinor = ratio if ratio in (1, 2) else 1
        c = Candidate(int(sp), int(ff), int(nb), int(bpp), int(mpi), float(weight), npspinor=npspinor, source="autoparal")
        key = (c.np_spkpt, c.npfft, c.npband, c.bandpp, c.mpi, c.weight, c.npspinor)
        if key not in seen:
            seen.add(key)
            candidates.append(c)
    return candidates


def run_autoparal_probe(
    inp: Path,
    *,
    max_cpus: int,
    abinit: str,
    probe_prefix: Callable[[int], list[str]],
    timeout: int = 180,
    npfft_fixed: int | None = None,
) -> tuple[list[Candidate], str]:
    """Run ABINIT's own autoparal search with a single MPI process.

    ``probe_prefix(1)`` returns the scheduler/MPI launcher tokens needed for one
    process. The temporary input is created beside the original so relative
    pseudopotential paths retain their meaning.
    """
    clean, _ = remove_global_kgb_lines(inp.read_text(errors="replace"))
    fixed = f"npfft {npfft_fixed}\n" if npfft_fixed is not None else ""
    probe_text = clean + f"\n# Added temporarily by Abi_KGB\n{fixed}autoparal 1\nmax_ncpus {max_cpus}\n"
    fd, name = tempfile.mkstemp(prefix=".abi_kgb_probe_", suffix=".abi", dir=inp.parent)
    os.close(fd)
    probe = Path(name)
    probe.write_text(probe_text)
    cmd = probe_prefix(1) + [abinit, probe.name]
    try:
        p = subprocess.run(
            cmd,
            cwd=inp.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = p.stdout or ""
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout if isinstance(exc.stdout, str) else ""
        raise RuntimeError(f"autoparal probe exceeded {timeout}s\n{partial[-4000:]}") from exc
    finally:
        stem = probe.stem
        try:
            probe.unlink()
        except OSError:
            pass
        for pth in inp.parent.glob(stem + "*"):
            try:
                if pth.is_file():
                    pth.unlink()
            except OSError:
                pass
    candidates = parse_autoparal_text(output)
    if not candidates:
        tail = "\n".join(output.splitlines()[-35:])
        raise RuntimeError("ABINIT autoparal table was not found. Last output lines:\n" + tail)
    return candidates, output
