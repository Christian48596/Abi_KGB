from __future__ import annotations

import argparse
import re
from pathlib import Path

from ..models import Calibration


def parse_calibration(spec: str) -> Calibration:
    parts = spec.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("calibration must be RANKS_PER_NODE:RSS_GIB_PER_NODE")
    try:
        ranks, rss = int(parts[0]), float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if ranks < 1 or rss <= 0:
        raise argparse.ArgumentTypeError("calibration values must be positive")
    return Calibration(ranks, rss)


def peak_rss_from_memory_log(path: Path) -> float | None:
    pat = re.compile(r"abinit_RSS_GiB=([0-9.]+)")
    vals: list[float] = []
    for line in path.read_text(errors="replace").splitlines():
        m = pat.search(line)
        if m:
            vals.append(float(m.group(1)))
    return max(vals) if vals else None


def fit_memory(calibrations: list[Calibration], ranks_per_node: int) -> float | None:
    """Fit a deliberately simple per-node RSS model.

    The model is empirical and never presented as an OOM guarantee. With one
    point it scales conservatively for larger rank counts and keeps the observed
    RSS for smaller counts. With >=2 points it fits M=a+b*r with non-negative
    intercept and slope.
    """
    if not calibrations:
        return None
    pts = [(c.ranks_per_node, c.rss_gib_per_node) for c in calibrations]
    if len(pts) == 1:
        r0, m0 = pts[0]
        return m0 * max(1.0, ranks_per_node / r0)
    xs = [float(x) for x, _ in pts]
    ys = [float(y) for _, y in pts]
    xm = sum(xs) / len(xs)
    ym = sum(ys) / len(ys)
    den = sum((x - xm) ** 2 for x in xs)
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / den if den else 0.0
    slope = max(0.0, slope)
    intercept = max(0.0, ym - slope * xm)
    return intercept + slope * ranks_per_node
