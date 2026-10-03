"""Explicit, fail-closed evidence sufficiency policy for Cogent analyses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from .models import Challenge, Observation, Outcome, ValidatorProfile


class EvidenceStatus(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class EvidenceRequirements:
    """All thresholds are caller-configurable and emitted in every analysis."""

    min_labelled_challenges: int = 10
    min_observed_labelled_challenges: int = 10
    min_challenge_families: int = 2
    min_observations_per_validator: int = 10
    min_overlapping_events_per_pair: int = 5
    min_informative_failures: int = 2
    min_shared_failures_for_correlation: int = 2
    min_repetitions_for_stochastic_engine: int = 1

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def assess_evidence(
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    observations: list[Observation],
    requirements: EvidenceRequirements,
) -> dict:
    labelled = [item for item in challenges if item.expected in (Outcome.ACCEPT, Outcome.REJECT)]
    labelled_ids = {item.id for item in labelled}
    by_validator = {item.id: 0 for item in validators}
    event_validators: dict[tuple[str, str], set[str]] = {}
    failures_by_validator = {item.id: 0 for item in validators}
    challenge_map = {item.id: item for item in challenges}
    repetitions: dict[str, set[str]] = {}
    observed_labelled: set[str] = set()
    matrix: dict[str, set[str]] = {item.id: set() for item in validators}
    for observation in observations:
        if observation.challenge_id in labelled_ids:
            observed_labelled.add(observation.challenge_id)
            matrix.setdefault(observation.validator_id, set()).add(observation.challenge_id)
            by_validator[observation.validator_id] = by_validator.get(observation.validator_id, 0) + 1
            repetitions.setdefault(observation.challenge_id, set()).add(observation.run_id)
            expected = challenge_map[observation.challenge_id].expected
            if observation.outcome not in (Outcome.ERROR, Outcome.TIMEOUT, Outcome.UNDETERMINED) and observation.outcome != expected:
                failures_by_validator[observation.validator_id] = failures_by_validator.get(observation.validator_id, 0) + 1
            event_validators.setdefault(observation.event_key, set()).add(observation.validator_id)

    pair_overlaps: list[int] = []
    ids = [item.id for item in validators]
    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            pair_overlaps.append(sum(left in members and right in members for members in event_validators.values()))
    minimum_overlap = min(pair_overlaps, default=0)
    minimum_repetitions = min((len(value) for value in repetitions.values()), default=0)
    fully_covered = sorted(
        challenge_id for challenge_id in labelled_ids
        if all(challenge_id in matrix.get(validator.id, set()) for validator in validators)
    )
    checks = {
        "labelled_challenges": {"actual": len(labelled), "required": requirements.min_labelled_challenges},
        "observed_labelled_challenges": {"actual": len(observed_labelled), "required": requirements.min_observed_labelled_challenges},
        "fully_covered_labelled_challenges": {"actual": len(fully_covered), "required": requirements.min_observed_labelled_challenges},
        "challenge_families": {"actual": len({item.family for item in labelled}), "required": requirements.min_challenge_families},
        "observations_per_validator": {"actual": min(by_validator.values(), default=0), "required": requirements.min_observations_per_validator},
        "overlapping_events_per_pair": {"actual": minimum_overlap, "required": requirements.min_overlapping_events_per_pair},
        "informative_semantic_failures_per_validator": {"actual": min(failures_by_validator.values(), default=0), "required": requirements.min_informative_failures},
        "repetitions": {"actual": minimum_repetitions, "required": requirements.min_repetitions_for_stochastic_engine},
    }
    for check in checks.values():
        check["pass"] = check["actual"] >= check["required"]
    failed = [name for name, check in checks.items() if not check["pass"]]
    status = EvidenceStatus.SUFFICIENT if not failed else EvidenceStatus.LIMITED
    if not observed_labelled or not fully_covered or min(failures_by_validator.values(), default=0) == 0:
        status = EvidenceStatus.INSUFFICIENT
    return {
        "status": status.value,
        "requirements": requirements.to_dict(),
        "checks": checks,
        "declared_labelled_challenges": len(labelled),
        "observed_labelled_challenges": len(observed_labelled),
        "fully_covered_labelled_challenges": len(fully_covered),
        "coverage_ratio": len(fully_covered) / len(labelled) if labelled else 0.0,
        "missing_challenges": sorted(labelled_ids - set(fully_covered)),
        "limitations": [f"{name} below configured minimum" for name in failed],
        "correlation_claims_permitted": status is EvidenceStatus.SUFFICIENT,
        "diversity_claims_permitted": status is EvidenceStatus.SUFFICIENT,
    }
