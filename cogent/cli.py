from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from importlib import resources

from .analysis import AnalysisConfig, analyze
from .certification import certify_validator
from .drift import drift_report
from .errors import CogentError, ConfigError
from .genlayer import public_transaction_context, validate_with_gltest
from .io import load_corpus, load_fleet, load_observations, write_json, write_jsonl
from .reporting import write_report
from .runner import run_matrix, runner_contract_example


def _float_01(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("expected a value between 0 and 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cogent",
        description=(
            "Behavioral independence, correlated-failure, drift, and committee-risk analysis "
            "for GenLayer validator fleets."
        ),
    )
    parser.add_argument("--version", action="version", version="cogent-gl 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a starter fleet, challenge corpus, and runner")
    init.add_argument("directory", nargs="?", default="cogent-lab")
    init.add_argument("--force", action="store_true")

    validate = sub.add_parser("validate", help="validate fleet/corpus/observation files")
    validate.add_argument("--fleet", required=True)
    validate.add_argument("--corpus", required=True)
    validate.add_argument("--observations")
    validate.add_argument("--gltest", action="store_true", help="round-trip profiles through genlayer-test")

    contexts = sub.add_parser("contexts", help="export gltest-compatible validator transaction contexts")
    contexts.add_argument("--fleet", required=True)
    contexts.add_argument("--output", required=True)
    contexts.add_argument("--genvm-datetime")
    contexts.add_argument(
        "--individual",
        action="store_true",
        help="emit one single-validator context per profile instead of one fleet context",
    )

    contract = sub.add_parser("runner-contract", help="print the external runner interface contract")
    contract.add_argument("--json", action="store_true")

    run = sub.add_parser("run", help="execute a validator × challenge matrix through an external runner")
    run.add_argument("--fleet", required=True)
    run.add_argument("--corpus", required=True)
    run.add_argument("--runner", required=True, help='command, e.g. "python experiments/run_case.py"')
    run.add_argument("--output", default="cogent-observations.jsonl")
    run.add_argument("--repetitions", type=int, default=1)
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--timeout", type=float, default=120.0)
    run.add_argument("--workers", type=int, default=1)

    analyze_cmd = sub.add_parser("analyze", help="analyze empirical validator observations")
    analyze_cmd.add_argument("--fleet", required=True)
    analyze_cmd.add_argument("--corpus", required=True)
    analyze_cmd.add_argument("--observations", required=True)
    analyze_cmd.add_argument("--output-dir", default="cogent-report")
    analyze_cmd.add_argument("--cluster-threshold", type=_float_01, default=0.75)
    analyze_cmd.add_argument("--min-shared-failures", type=int, default=2)
    analyze_cmd.add_argument("--committee-size", type=int)
    analyze_cmd.add_argument("--simulations", type=int, default=5000)
    analyze_cmd.add_argument("--seed", type=int, default=7)

    simulate = sub.add_parser("simulate", help="run analysis and print only committee-risk metrics")
    simulate.add_argument("--fleet", required=True)
    simulate.add_argument("--corpus", required=True)
    simulate.add_argument("--observations", required=True)
    simulate.add_argument("--committee-size", type=int, default=5)
    simulate.add_argument("--simulations", type=int, default=10000)
    simulate.add_argument("--seed", type=int, default=7)
    simulate.add_argument("--cluster-threshold", type=_float_01, default=0.75)
    simulate.add_argument("--min-shared-failures", type=int, default=2)

    drift = sub.add_parser("drift", help="compare two observation datasets for behavioral drift")
    drift.add_argument("--corpus", required=True)
    drift.add_argument("--baseline", required=True)
    drift.add_argument("--current", required=True)
    drift.add_argument("--output", default="cogent-drift.json")

    certify = sub.add_parser("certify", help="apply local readiness thresholds to one validator")
    certify.add_argument("--analysis", required=True)
    certify.add_argument("--validator", required=True)
    certify.add_argument("--max-failure-rate", type=_float_01, default=0.05)
    certify.add_argument("--max-operational-failure-rate", type=_float_01, default=0.02)
    certify.add_argument("--max-cluster-size", type=int)

    ci = sub.add_parser("ci", help="fail CI when empirical fleet thresholds are violated")
    ci.add_argument("--analysis", required=True)
    ci.add_argument("--min-normalized-diversity", type=_float_01, default=0.5)
    ci.add_argument("--max-correlated-majority-rate", type=_float_01, default=0.25)
    ci.add_argument("--max-wrong-majority-rate", type=_float_01, default=0.05)

    return parser


def _init_project(directory: str, force: bool) -> None:
    root = Path(directory)
    if root.exists() and any(root.iterdir()) and not force:
        raise ConfigError(f"{root} is not empty; use --force to overwrite starter files")
    root.mkdir(parents=True, exist_ok=True)
    template_root = resources.files("cogent.templates")
    for source_name, dest_name in [
        ("fleet.yaml", "fleet.yaml"),
        ("corpus.yaml", "corpus.yaml"),
        ("runner.py", "runner.py"),
    ]:
        content = template_root.joinpath(source_name).read_text(encoding="utf-8")
        (root / dest_name).write_text(content, encoding="utf-8")
    print(f"initialized Cogent lab at {root}")
    print("next: cogent run --fleet fleet.yaml --corpus corpus.yaml --runner 'python runner.py'")


def _analysis_from_args(args: argparse.Namespace) -> dict:
    validators = load_fleet(args.fleet)
    challenges = load_corpus(args.corpus)
    observations = load_observations(args.observations)
    return analyze(
        validators,
        challenges,
        observations,
        AnalysisConfig(
            cluster_threshold=args.cluster_threshold,
            min_shared_failures=args.min_shared_failures,
            committee_size=args.committee_size,
            simulations=args.simulations,
            seed=args.seed,
        ),
    )


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "init":
        _init_project(args.directory, args.force)
        return 0

    if args.command == "validate":
        validators = load_fleet(args.fleet)
        challenges = load_corpus(args.corpus)
        observations = load_observations(args.observations) if args.observations else []
        if args.gltest:
            for validator in validators:
                validate_with_gltest(validator)
        print(
            json.dumps(
                {
                    "valid": True,
                    "validators": len(validators),
                    "challenges": len(challenges),
                    "observations": len(observations),
                    "gltest_roundtrip": bool(args.gltest),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "contexts":
        validators = load_fleet(args.fleet)
        if args.individual:
            data = {
                item.id: public_transaction_context([item], genvm_datetime=args.genvm_datetime)
                for item in validators
            }
        else:
            data = public_transaction_context(validators, genvm_datetime=args.genvm_datetime)
        write_json(args.output, data)
        print(f"wrote {args.output}")
        return 0

    if args.command == "runner-contract":
        payload = runner_contract_example()
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "run":
        validators = load_fleet(args.fleet)
        challenges = load_corpus(args.corpus)
        observations = run_matrix(
            args.runner,
            validators,
            challenges,
            repetitions=args.repetitions,
            global_seed=args.seed,
            timeout_seconds=args.timeout,
            workers=args.workers,
        )
        write_jsonl(args.output, (item.to_dict() for item in observations))
        counts = {}
        for item in observations:
            counts[item.outcome.value] = counts.get(item.outcome.value, 0) + 1
        print(json.dumps({"output": args.output, "observations": len(observations), "outcomes": counts}, indent=2))
        return 0

    if args.command == "analyze":
        result = _analysis_from_args(args)
        output_dir = Path(args.output_dir)
        write_json(output_dir / "analysis.json", result)
        write_report(output_dir / "report.md", result)
        print(json.dumps({"output_dir": str(output_dir), "diversity": result["diversity"], "committee_simulation": result["committee_simulation"]}, indent=2))
        return 0

    if args.command == "simulate":
        result = _analysis_from_args(args)
        print(json.dumps(result["committee_simulation"], indent=2))
        return 0

    if args.command == "drift":
        challenges = load_corpus(args.corpus)
        baseline = load_observations(args.baseline)
        current = load_observations(args.current)
        result = drift_report(challenges, baseline, current)
        write_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "certify":
        analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
        result = certify_validator(
            analysis,
            args.validator,
            max_failure_rate=args.max_failure_rate,
            max_operational_failure_rate=args.max_operational_failure_rate,
            max_cluster_size=args.max_cluster_size,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 2

    if args.command == "ci":
        analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
        diversity = float(analysis["diversity"]["normalized_diversity"])
        simulation = analysis["committee_simulation"]
        correlated = float(simulation["correlated_cluster_majority_rate"])
        wrong = simulation.get("wrong_majority_rate")
        checks = {
            "normalized_diversity": diversity >= args.min_normalized_diversity,
            "correlated_majority_rate": correlated <= args.max_correlated_majority_rate,
            "wrong_majority_rate": wrong is not None and float(wrong) <= args.max_wrong_majority_rate,
        }
        print(json.dumps({"passed": all(checks.values()), "checks": checks}, indent=2))
        return 0 if all(checks.values()) else 3

    raise ConfigError(f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return dispatch(args)
    except (CogentError, ValueError, OSError) as exc:
        print(f"cogent: error: {exc}", file=sys.stderr)
        return 2
