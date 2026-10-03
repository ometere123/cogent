from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .clustering import annotate_cluster_failures, build_clusters, diversity_metrics
from .committee import simulate_committees
from .evidence import EvidenceRequirements, assess_evidence
from .metrics import challenge_metrics, pairwise_metrics, validator_metrics
from .models import Challenge, Observation, ValidatorProfile


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    cluster_threshold: float = 0.75
    min_shared_failures: int = 2
    committee_size: int | None = None
    simulations: int = 5000
    seed: int = 7
    evidence_requirements: EvidenceRequirements = EvidenceRequirements()


def analyze(
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    observations: list[Observation],
    config: AnalysisConfig | None = None,
) -> dict:
    config = config or AnalysisConfig()
    validator_ids = {item.id for item in validators}
    challenge_ids = {item.id for item in challenges}
    unknown_validators = sorted({item.validator_id for item in observations} - validator_ids)
    unknown_challenges = sorted({item.challenge_id for item in observations} - challenge_ids)
    if unknown_validators:
        raise ValueError(f"observations reference unknown validators: {unknown_validators}")
    if unknown_challenges:
        raise ValueError(f"observations reference unknown challenges: {unknown_challenges}")

    evidence = assess_evidence(validators, challenges, observations, config.evidence_requirements)
    pairwise = pairwise_metrics(validators, challenges, observations)
    clusters_by_channel = {}
    for channel in ("semantic_failure", "operational_failure", "availability_failure", "combined_failure"):
        built = build_clusters(validators, pairwise, threshold=config.cluster_threshold,
                               min_shared_failures=config.min_shared_failures, channel=channel)
        clusters_by_channel[channel] = annotate_cluster_failures(built, challenges, observations)
    clusters = clusters_by_channel["combined_failure"]
    committee_size = config.committee_size or min(5, len(validators))
    simulation = simulate_committees(
        validators,
        challenges,
        observations,
        clusters,
        committee_size=committee_size,
        simulations=config.simulations,
        seed=config.seed,
    )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "methodology": {
            "cluster_threshold": config.cluster_threshold,
            "min_shared_failures": config.min_shared_failures,
            "correlation_basis": "co-failure Jaccard / phi on labeled challenge executions",
            "diversity_basis": "inverse-Simpson effective count over stake share of empirical failure clusters",
            "scope_warning": (
                "Results describe this fleet on this challenge corpus. They are not a claim of "
                "protocol-wide independence, validator honesty, or future consensus probability."
            ),
        },
        "fleet": {
            "validators": len(validators),
            "total_stake_weight": sum(item.stake for item in validators),
        },
        "corpus": {
            "challenges": len(challenges),
            "families": sorted({item.family for item in challenges}),
            "observations": len(observations),
        },
        "validators": validator_metrics(validators, challenges, observations),
        "challenges": challenge_metrics(challenges, observations),
        "pairwise": pairwise,
        "clusters": clusters,
        "clusters_by_channel": clusters_by_channel,
        "evidence_sufficiency": evidence,
        "diversity": diversity_metrics(
            validators, clusters, evidence_status=evidence["status"],
        ),
        "committee_simulation": simulation,
    }
