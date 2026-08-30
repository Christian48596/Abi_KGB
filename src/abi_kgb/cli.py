from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import shlex
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .abinit import assess_kgb_compatibility, parse_abi, parse_autoparal_text, patch_kgb_block, run_autoparal_probe
from .detection import detect_abinit, detect_mpi, detect_system
from .doctor import doctor_report, print_doctor
from .launchers import select_launcher
from .models import Calibration, RankedCandidate
from .optimization import parse_calibration, peak_rss_from_memory_log, rank_candidates, static_candidates
from .schedulers import detect_scheduler, resource_envelope
from .writers import local_nohup_command, write_run_script


def _jsonable(value):
    if dataclasses.is_dataclass(value):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _probe_prefix(plan, scheduler_info):
    def prefix(ranks: int) -> list[str]:
        text = plan.command_template.format(ranks=ranks)
        toks = shlex.split(text)
        if scheduler_info.nodefile:
            toks = [scheduler_info.nodefile if t == "$PBS_NODEFILE" else t for t in toks]
        return toks
    return prefix


def _print_report(system, mpi, abi, sched, resources, info, plan, ranked: list[RankedCandidate],
                  reserve: float, top: int, npfft_fixed: int | None):
    print("\nAbi_KGB 1.0.0 — portable ABINIT KGB advisor")
    print("=" * 72)
    print(f"Host                 : {system.hostname}{' (WSL)' if system.is_wsl else ''}")
    print(f"CPU                  : {system.cpu_model or '?'}")
    print(f"Physical/logical CPU : {system.physical_cores or '?'} / {system.logical_cpus}")
    print(f"NUMA nodes           : {system.numa_nodes or '?'}")
    print(f"RAM avail./limit     : {system.mem_available_gib:.2f} / {system.mem_effective_limit_gib:.2f} GiB")
    print(f"Scheduler            : {sched.kind}{' (active allocation)' if sched.active_allocation else ''}")
    if sched.partition_or_queue:
        print(f"Partition/queue      : {sched.partition_or_queue}")
    print(f"Resource source      : {resources.source}")
    print(f"Target resources     : {resources.nodes} node(s), <= {resources.max_total_ranks} MPI ranks, <= {resources.max_ranks_per_node}/node")
    print(f"RAM/node             : {resources.memory_per_node_gib:.2f} GiB" if resources.memory_per_node_gib is not None else "RAM/node             : unknown")
    print(f"MPI                  : {mpi.family} | {mpi.launcher_path or 'NOT FOUND'}")
    print(f"ABINIT               : {abi.version or '?'} | {abi.executable or 'NOT FOUND'}")
    print(f"Launch strategy      : {plan.command_template}")
    print(f"Input                : {info.path}")
    print(f"ndtset/optdriver     : {info.ndtset} / {info.optdriver}")
    print(f"nband                : {info.nband if info.nband is not None else '?'}")
    if info.spin_k is not None:
        print(f"nkpt × nsppol        : {info.nkpt} × {info.nsppol} = {info.spin_k}")
    else:
        print(f"nkpt × nsppol        : ? × {info.nsppol}")
    print(f"nspinor/npspinor     : {info.nspinor}/{info.npspinor}")
    print(f"ecut/pawecutdg       : {info.ecut_ha if info.ecut_ha is not None else '?'} / {info.pawecutdg_ha if info.pawecutdg_ha is not None else '?'} Ha")
    print(f"PAW-like input       : {'yes' if info.likely_paw else 'not inferred'}")
    if npfft_fixed is not None:
        print(f"Fixed npfft          : {npfft_fixed}")
    print(f"Memory safety reserve: {reserve:.0%}")
    for w in plan.warnings:
        print(f"LAUNCH WARNING       : {w}")

    if not ranked:
        print("\nNo legal candidate survived the requested resource filters.")
        return
    print("\nTop candidates")
    print("-" * 104)
    print(f"{'#':>2} {'MPI':>5} {'spkpt':>6} {'band':>5} {'fft':>4} {'spinor':>6} {'bandpp':>6} {'ABINIT W':>9} {'RSS/node':>10} {'Mem':>8} {'Score':>7}")
    for i, r in enumerate(ranked[:top], 1):
        rss = "?" if r.estimated_rss_per_node_gib is None else f"{r.estimated_rss_per_node_gib:.1f}G"
        c = r.candidate
        print(f"{i:>2} {c.mpi:>5} {c.np_spkpt:>6} {c.npband:>5} {c.npfft:>4} {c.npspinor:>6} {c.bandpp:>6} {c.weight:>9.3f} {rss:>10} {r.memory_status:>8} {r.score:>7.1f}")
        for note in r.notes:
            print(f"     note: {note}")
    viable = [r for r in ranked if r.memory_status != "REJECT"]
    if not viable:
        print("\nNo recommendation: every candidate is rejected by the calibrated memory budget.")
        return
    best = viable[0]
    c = best.candidate
    print("\nRecommended ABINIT block")
    print("-" * 72)
    print("paral_kgb 1")
    print(f"np_spkpt {c.np_spkpt}")
    print(f"npband {c.npband}")
    print(f"npfft {c.npfft}")
    print(f"bandpp {c.bandpp}")
    if c.npspinor != 1:
        print(f"npspinor {c.npspinor}")
    print(f"# MPI ranks = {c.mpi}")
    if best.memory_status == "UNKNOWN":
        print("\nMemory verdict: UNKNOWN. Abi_KGB does not claim OOM safety without an empirical RSS calibration or a reliable site memory model.")
    elif best.estimated_rss_per_node_gib is not None:
        print(f"\nMemory verdict: {best.memory_status}; empirical estimate ≈ {best.estimated_rss_per_node_gib:.1f} GiB/node.")


def _doctor_main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="abi-kgb doctor", description="Inspect the local ABINIT/MPI/scheduler environment")
    p.add_argument("--scheduler", choices=["auto", "local", "slurm", "pbs"], default="auto")
    p.add_argument("--partition")
    p.add_argument("--queue")
    p.add_argument("--abinit")
    p.add_argument("--mpi-launcher")
    p.add_argument("--launcher", choices=["auto", "mpiexec", "mpirun", "srun"], default="auto")
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    report = doctor_report(scheduler=args.scheduler, partition=args.partition, queue=args.queue,
                           abinit=args.abinit, mpi_launcher=args.mpi_launcher, launcher=args.launcher)
    print_doctor(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2))
        print(f"\nWrote {args.json}")
    return 0


def _advise_main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="abi-kgb",
        description="Detect resources, ask ABINIT for legal autoparal layouts, rank KGB decompositions, and generate local/SLURM/PBS launch files.",
    )
    p.add_argument("input", type=Path, help="single-dataset ABINIT .abi input")
    p.add_argument("--scheduler", choices=["auto", "local", "slurm", "pbs"], default="auto")
    p.add_argument("--partition", help="SLURM partition (also selects SLURM when --scheduler=auto)")
    p.add_argument("--queue", help="PBS queue (also selects PBS when --scheduler=auto)")
    p.add_argument("--nodes", type=int)
    p.add_argument("--max-cpus", type=int, help="maximum total MPI ranks considered")
    p.add_argument("--ranks-per-node", type=int)
    p.add_argument("--memory-per-node", type=float, help="GiB available/requested per node")
    p.add_argument("--allow-smt", action="store_true", help="on local systems allow default rank cap to use hardware threads")
    p.add_argument("--reserve", type=float, default=0.20, help="fraction of RAM reserved from calibrated memory budget (default: 0.20)")
    p.add_argument("--abinit", help="ABINIT executable path/name")
    p.add_argument("--mpi-launcher", help="MPI executable used for detection, e.g. mpiexec or mpirun")
    p.add_argument("--launcher", choices=["auto", "mpiexec", "mpirun", "srun"], default="auto", help="force generated launch mechanism")
    p.add_argument("--npfft-fixed", type=int, help="fix npfft during ABINIT autoparal search (e.g. 1 for FFT-fragile builds)")
    p.add_argument("--npfft-max", type=int, help="discard candidates with npfft above this value")
    p.add_argument("--autoparal-log", type=Path, help="use an existing ABINIT autoparal log instead of a live probe")
    p.add_argument("--no-autoparal", action="store_true", help="disable live probe and use algebraic fallback; requires explicit nkpt and nband")
    p.add_argument("--autoparal-timeout", type=int, default=180)
    p.add_argument("--calibration", action="append", default=[], type=parse_calibration,
                   help="empirical RANKS_PER_NODE:PEAK_RSS_GIB_PER_NODE; repeat for multiple measurements")
    p.add_argument("--memory-log", type=Path, help="memory monitor log containing abinit_RSS_GiB=...")
    p.add_argument("--memory-log-ranks", type=int, help="ranks/node corresponding to --memory-log")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--write", action="store_true", help="write recommended .kgb.abi and launch script")
    p.add_argument("--write-dir", type=Path, default=Path("."))
    p.add_argument("--walltime", help="optional scheduler walltime, e.g. 48:00:00")
    p.add_argument("--job-name")
    p.add_argument("--module", action="append", default=[], help="module to load in generated batch script; repeat as needed")
    p.add_argument("--json", type=Path, help="write machine-readable report")
    args = p.parse_args(argv)

    if not args.input.exists():
        p.error(f"input not found: {args.input}")
    if not 0 <= args.reserve < 0.8:
        p.error("--reserve must be in [0, 0.8)")
    for name in ("nodes", "max_cpus", "ranks_per_node", "npfft_fixed", "npfft_max"):
        value = getattr(args, name)
        if value is not None and value < 1:
            p.error(f"--{name.replace('_', '-')} must be >= 1")

    system = detect_system()
    mpi = detect_mpi(args.mpi_launcher)
    abi = detect_abinit(args.abinit)
    if not abi.executable:
        p.error("ABINIT executable not found; use --abinit /path/to/abinit")
    if mpi.family == "none" and not args.autoparal_log and not args.no_autoparal:
        p.error("MPI launcher not found; use --mpi-launcher or --autoparal-log")

    backend, sched = detect_scheduler(args.scheduler, partition=args.partition, queue=args.queue)
    resources = resource_envelope(
        backend,
        system,
        nodes=args.nodes,
        max_cpus=args.max_cpus,
        ranks_per_node=args.ranks_per_node,
        memory_per_node=args.memory_per_node,
        partition_or_queue=args.partition or args.queue,
        allow_smt=args.allow_smt,
    )
    plan = select_launcher(mpi, sched, args.launcher)
    info = parse_abi(args.input.resolve())
    compatible, reasons = assess_kgb_compatibility(info)
    if not compatible:
        print("Abi_KGB cannot safely advise this input:", file=sys.stderr)
        for reason in reasons:
            print(f"  - {reason}", file=sys.stderr)
        return 3

    calibrations: list[Calibration] = list(args.calibration)
    if args.memory_log:
        if not args.memory_log_ranks:
            p.error("--memory-log requires --memory-log-ranks")
        peak = peak_rss_from_memory_log(args.memory_log)
        if peak is None:
            p.error("no abinit_RSS_GiB samples found in --memory-log")
        calibrations.append(Calibration(args.memory_log_ranks, peak))

    if args.autoparal_log:
        candidates = parse_autoparal_text(args.autoparal_log.read_text(errors="replace"))
        if not candidates:
            p.error("no ABINIT autoparal table found in supplied log")
    elif args.no_autoparal:
        candidates = static_candidates(info, resources.max_total_ranks, npfft_max=args.npfft_fixed or args.npfft_max or 8)
        if not candidates:
            p.error("algebraic fallback needs explicit global nkpt and nband; use a live autoparal probe instead")
    elif sched.kind in {"slurm", "pbs"} and not sched.active_allocation:
        print(
            f"WARNING: {sched.kind.upper()} detected/requested but Abi_KGB is not inside a compute allocation; refusing to execute ABINIT on a login host.",
            file=sys.stderr,
        )
        print("Use --autoparal-log, start an interactive compute allocation, or use --no-autoparal when nkpt/nband are explicit.", file=sys.stderr)
        candidates = static_candidates(info, resources.max_total_ranks, npfft_max=args.npfft_fixed or args.npfft_max or 8)
        if not candidates:
            return 4
    else:
        try:
            candidates, _ = run_autoparal_probe(
                info.path,
                max_cpus=resources.max_total_ranks,
                abinit=abi.executable,
                probe_prefix=_probe_prefix(plan, sched),
                timeout=args.autoparal_timeout,
                npfft_fixed=args.npfft_fixed,
            )
        except Exception as exc:
            print(f"WARNING: live ABINIT autoparal probe failed: {exc}", file=sys.stderr)
            candidates = static_candidates(info, resources.max_total_ranks, npfft_max=args.npfft_fixed or args.npfft_max or 8)
            if not candidates:
                return 5

    if args.npfft_fixed is not None:
        candidates = [c for c in candidates if c.npfft == args.npfft_fixed]
        if not candidates:
            print(f"ERROR: no candidate with npfft={args.npfft_fixed}", file=sys.stderr)
            return 2

    ranked = rank_candidates(
        candidates,
        system=system,
        resources=resources,
        reserve_fraction=args.reserve,
        npfft_max=args.npfft_max,
        calibrations=calibrations,
        prefer_physical=not args.allow_smt,
    )
    _print_report(system, mpi, abi, sched, resources, info, plan, ranked, args.reserve, args.top, args.npfft_fixed)

    viable = [r for r in ranked if r.memory_status != "REJECT"]
    if not viable:
        return 2
    best = viable[0]

    generated: dict[str, str] = {}
    if args.write:
        args.write_dir.mkdir(parents=True, exist_ok=True)
        out_input = args.write_dir / f"{args.input.stem}.kgb.abi"
        removed = patch_kgb_block(info.path, out_input, best.candidate)
        if sched.kind == "slurm":
            run_script = args.write_dir / "run_kgb.slurm"
        elif sched.kind == "pbs":
            run_script = args.write_dir / "run_kgb.pbs"
        else:
            run_script = args.write_dir / "run_kgb.sh"
        write_run_script(
            run_script,
            input_path=out_input,
            candidate=best.candidate,
            scheduler=sched,
            launcher=plan,
            nodes=resources.nodes,
            ranks_per_node=math.ceil(best.candidate.mpi / resources.nodes),
            abinit=abi.executable,
            partition=args.partition,
            queue=args.queue,
            walltime=args.walltime,
            job_name=args.job_name,
            modules=args.module,
            pbs_flavor=sched.flavor,
        )
        print(f"\nWrote patched input : {out_input}")
        print(f"Wrote launch script : {run_script}")
        if removed:
            print(f"Replaced {len(removed)} existing global KGB/autoparal line(s).")
        if sched.kind == "slurm":
            print(f"Submit with          : sbatch {run_script}")
        elif sched.kind == "pbs":
            print(f"Submit with          : qsub {run_script}")
        else:
            print(f"Background command   : {local_nohup_command(run_script)}")
        generated = {"input": str(out_input), "script": str(run_script)}

    if args.json:
        payload = {
            "version": __version__,
            "system": _jsonable(system),
            "mpi": _jsonable(mpi),
            "abinit": _jsonable(abi),
            "scheduler": _jsonable(sched),
            "resources": _jsonable(resources),
            "input": _jsonable(info),
            "launcher": _jsonable(plan),
            "calibrations": _jsonable(calibrations),
            "recommendation": _jsonable(best),
            "top_candidates": _jsonable(ranked[: args.top]),
            "generated": generated,
        }
        args.json.write_text(json.dumps(payload, indent=2))
        print(f"Wrote JSON report    : {args.json}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: abi-kgb INPUT.abi [options]\n       abi-kgb doctor [options]\n       abi-kgb --version")
        return 0
    if args[0] in {"--version", "-V"}:
        print(f"Abi_KGB {__version__}")
        return 0
    if args[0] == "doctor":
        return _doctor_main(args[1:])
    return _advise_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
