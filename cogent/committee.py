from __future__ import annotations

import random
from collections import Counter

from .models import Challenge, Observation, Outcome, ValidatorProfile


def _weighted_sample_without_replacement(
    rng: random.Random, validators: list[ValidatorProfile], size: int
) -> list[ValidatorProfile]:
    if size > len(validators):
        raise ValueError("committee size cannot exceed fleet size")
    # Efraimidis-Spirakis weighted reservoir keys.
    ranked = []
    for validator in validators:
        draw = max(rng.random(), 1e-15)
        key = draw ** (1.0 / validator.stake)
        ranked.append((key, validator))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [validator for _, validator in ranked[:size]]


def simulate_committees(
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    observations: list[Observation],
    clusters: list[dict],
    *,
    committee_size: int = 5,
    simulations: int = 5000,
    seed: int = 7,
) -> dict:
    if committee_size <= 0:
        raise ValueError("committee size must be positive")
    if committee_size > len(validators):
        raise ValueError("committee size cannot exceed fleet size")
    if simulations <= 0:
        raise ValueError("simulations must be positive")

    challenge_map = {item.id: item for item in challenges}
    obs_map = {
        (item.validator_id, item.challenge_id, item.run_id): item for item in observations
    }
    event_keys = sorted({(item.challenge_id, item.run_id) for item in observations})
    cluster_of = {
        validator_id: cluster["id"]
        for cluster in clusters
        for validator_id in cluster["validators"]
    }
    rng = random.Random(seed)
    majority = committee_size // 2 + 1
    correlated_majority = 0
    evaluated = 0
    wrong_majority = 0
    correct_majority = 0
    undetermined = 0

    for _ in range(simulations):
        committee = _weighted_sample_without_replacement(rng, validators, committee_size)
        cluster_counts = Counter(cluster_of.get(item.id, item.id) for item in committee)
        if max(cluster_counts.values(), default=0) >= majority:
            correlated_majority += 1

        if not event_keys:
            continue
        challenge_id, run_id = event_keys[rng.randrange(len(event_keys))]
        challenge = challenge_map.get(challenge_id)
        if challenge is None or challenge.expected is None:
            continue
        votes = Counter()
        complete = True
        for validator in committee:
            observation = obs_map.get((validator.id, challenge_id, run_id))
            if observation is None:
                complete = False
                break
            if observation.outcome in (Outcome.ACCEPT, Outcome.REJECT):
                votes[observation.outcome] += 1
        if not complete:
            continue
        evaluated += 1
        outcome = None
        if votes[Outcome.ACCEPT] >= majority:
            outcome = Outcome.ACCEPT
        elif votes[Outcome.REJECT] >= majority:
            outcome = Outcome.REJECT
        if outcome is None:
            undetermined += 1
        elif outcome == challenge.expected:
            correct_majority += 1
        else:
            wrong_majority += 1

    return {
        "committee_size": committee_size,
        "simulations": simulations,
        "seed": seed,
        "majority_threshold": majority,
        "correlated_cluster_majority_rate": correlated_majority / simulations,
        "evaluated_consensus_samples": evaluated,
        "wrong_majority_rate": wrong_majority / evaluated if evaluated else None,
        "correct_majority_rate": correct_majority / evaluated if evaluated else None,
        "undetermined_rate": undetermined / evaluated if evaluated else None,
        "methodology": {
            "selection": "stake-weighted sampling without replacement",
            "behavior": "empirical replay over observed challenge outcomes",
            "claim_scope": "tested corpus only; not a protocol-level probability guarantee",
        },
    }
