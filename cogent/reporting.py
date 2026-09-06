from __future__ import annotations

from pathlib import Path


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def analysis_markdown(analysis: dict) -> str:
    diversity = analysis["diversity"]
    simulation = analysis["committee_simulation"]
    lines = [
        "# Cogent behavioral-independence report",
        "",
        "> Empirical result: this report characterizes the tested fleet on the tested challenge corpus. ",
        "> It is not a protocol guarantee, proof of validator honesty, or prediction of future model behavior.",
        "",
        "## Summary",
        "",
        f"- Validators: **{analysis['fleet']['validators']}**",
        f"- Challenges: **{analysis['corpus']['challenges']}** across {len(analysis['corpus']['families'])} families",
        f"- Observations: **{analysis['corpus']['observations']}**",
        f"- Empirical failure clusters: **{len(analysis['clusters'])}**",
        f"- Effective failure domains: **{diversity['effective_failure_domains']:.2f}**",
        f"- Normalized behavioral diversity: **{_pct(diversity['normalized_diversity'])}**",
        f"- Largest empirical cluster stake share: **{_pct(diversity['largest_cluster_share'])}**",
        "",
        "## Committee-risk simulation",
        "",
        f"- Committee size: **{simulation['committee_size']}**",
        f"- Simulations: **{simulation['simulations']}** (seed {simulation['seed']})",
        f"- Same-cluster majority rate: **{_pct(simulation['correlated_cluster_majority_rate'])}**",
        f"- Wrong-majority rate on evaluated corpus samples: **{_pct(simulation['wrong_majority_rate'])}**",
        f"- Undetermined rate on evaluated corpus samples: **{_pct(simulation['undetermined_rate'])}**",
        "",
        "## Validator metrics",
        "",
        "| Validator | Executions | Failure rate | Operational failure | Median latency |",
        "|---|---:|---:|---:|---:|",
    ]
    for validator_id, metrics in analysis["validators"].items():
        latency = metrics["median_latency_ms"]
        lines.append(
            f"| `{validator_id}` | {metrics['executions']} | {_pct(metrics['failure_rate'])} | "
            f"{_pct(metrics['operational_failure_rate'])} | "
            f"{'n/a' if latency is None else f'{latency:.1f} ms'} |"
        )
    lines.extend(["", "## Empirical failure clusters", ""])
    for cluster in analysis["clusters"]:
        members = ", ".join(f"`{item}`" for item in cluster["validators"])
        lines.append(f"### {cluster['id']} ({cluster['size']} validators)")
        lines.append("")
        lines.append(f"Members: {members}")
        lines.append("")
        families = cluster.get("dominant_failure_families") or []
        if families:
            lines.append("Dominant observed failure families:")
            lines.append("")
            for item in families:
                lines.append(f"- `{item['family']}`: {item['events']} failure events")
            lines.append("")
    lines.extend(
        [
            "## Methodology notes",
            "",
            f"- Cluster threshold: `{analysis['methodology']['cluster_threshold']}`",
            f"- Minimum shared failures: `{analysis['methodology']['min_shared_failures']}`",
            f"- Correlation basis: {analysis['methodology']['correlation_basis']}",
            f"- Diversity basis: {analysis['methodology']['diversity_basis']}",
            "",
            analysis["methodology"]["scope_warning"],
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: str | Path, analysis: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(analysis_markdown(analysis), encoding="utf-8")
