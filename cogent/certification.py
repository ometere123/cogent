from __future__ import annotations


def certify_validator(
    analysis: dict,
    validator_id: str,
    *,
    max_failure_rate: float = 0.05,
    max_operational_failure_rate: float = 0.02,
    max_cluster_size: int | None = None,
) -> dict:
    metrics = analysis.get("validators", {}).get(validator_id)
    if metrics is None:
        raise ValueError(f"validator not found in analysis: {validator_id}")
    checks = []

    failure = metrics.get("failure_rate")
    checks.append(
        {
            "name": "failure_rate",
            "pass": failure is not None and failure <= max_failure_rate,
            "actual": failure,
            "threshold": max_failure_rate,
        }
    )
    operational = metrics.get("operational_failure_rate")
    checks.append(
        {
            "name": "operational_failure_rate",
            "pass": operational is not None and operational <= max_operational_failure_rate,
            "actual": operational,
            "threshold": max_operational_failure_rate,
        }
    )

    cluster = next(
        (item for item in analysis.get("clusters", []) if validator_id in item["validators"]), None
    )
    if max_cluster_size is not None:
        size = cluster["size"] if cluster else 1
        checks.append(
            {
                "name": "cluster_size",
                "pass": size <= max_cluster_size,
                "actual": size,
                "threshold": max_cluster_size,
            }
        )

    return {
        "validator_id": validator_id,
        "passed": all(item["pass"] for item in checks),
        "checks": checks,
        "cluster": cluster,
        "scope_warning": "Certification is a local policy decision over this empirical Cogent run.",
    }
