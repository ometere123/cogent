from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import mean, median

from .models import Challenge, Observation, Outcome, ValidatorProfile


def _failure(observation: Observation, challenge: Challenge) -> bool | None:
    if challenge.expected is None:
        return None
    if observation.outcome in (Outcome.ERROR, Outcome.TIMEOUT, Outcome.UNDETERMINED):
        return True
    return observation.outcome != challenge.expected


def validator_metrics(
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    observations: list[Observation],
) -> dict[str, dict]:
    challenge_map = {item.id: item for item in challenges}
    by_validator: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        by_validator[observation.validator_id].append(observation)

    result: dict[str, dict] = {}
    for validator in validators:
        items = by_validator.get(validator.id, [])
        counts = Counter(item.outcome.value for item in items)
        known = 0
        failures = 0
        latencies = [item.latency_ms for item in items if item.latency_ms is not None]
        family_known: dict[str, int] = defaultdict(int)
        family_failures: dict[str, int] = defaultdict(int)
        for item in items:
            challenge = challenge_map.get(item.challenge_id)
            if challenge is None:
                continue
            failed = _failure(item, challenge)
            if failed is not None:
                known += 1
                family_known[challenge.family] += 1
                if failed:
                    failures += 1
                    family_failures[challenge.family] += 1
        operational_failures = counts[Outcome.ERROR.value] + counts[Outcome.TIMEOUT.value]
        result[validator.id] = {
            "executions": len(items),
            "accept": counts[Outcome.ACCEPT.value],
            "reject": counts[Outcome.REJECT.value],
            "undetermined": counts[Outcome.UNDETERMINED.value],
            "error": counts[Outcome.ERROR.value],
            "timeout": counts[Outcome.TIMEOUT.value],
            "known_expectation_executions": known,
            "failures": failures,
            "failure_rate": failures / known if known else None,
            "operational_failure_rate": operational_failures / len(items) if items else None,
            "mean_latency_ms": mean(latencies) if latencies else None,
            "median_latency_ms": median(latencies) if latencies else None,
            "family_failure_rates": {
                family: family_failures[family] / total
                for family, total in sorted(family_known.items())
                if total
            },
        }
    return result


def _phi(a: list[bool], b: list[bool]) -> float:
    n11 = sum(x and y for x, y in zip(a, b, strict=True))
    n10 = sum(x and not y for x, y in zip(a, b, strict=True))
    n01 = sum(not x and y for x, y in zip(a, b, strict=True))
    n00 = sum(not x and not y for x, y in zip(a, b, strict=True))
    denom = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    if denom == 0:
        return 0.0
    return (n11 * n00 - n10 * n01) / denom


def pairwise_metrics(
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    observations: list[Observation],
) -> list[dict]:
    challenge_map = {item.id: item for item in challenges}
    by_validator: dict[str, dict[tuple[str, str], Observation]] = defaultdict(dict)
    for observation in observations:
        by_validator[observation.validator_id][observation.event_key] = observation

    rows: list[dict] = []
    for index, left in enumerate(validators):
        for right in validators[index + 1 :]:
            left_events = by_validator.get(left.id, {})
            right_events = by_validator.get(right.id, {})
            shared = sorted(set(left_events) & set(right_events))
            if not shared:
                rows.append(
                    {
                        "left": left.id,
                        "right": right.id,
                        "overlap": 0,
                        "agreement_rate": None,
                        "failure_jaccard": None,
                        "failure_phi": None,
                        "shared_failures": 0,
                    }
                )
                continue

            agreement = sum(
                left_events[key].outcome == right_events[key].outcome for key in shared
            ) / len(shared)

            failure_a: list[bool] = []
            failure_b: list[bool] = []
            for key in shared:
                challenge = challenge_map.get(key[0])
                if challenge is None or challenge.expected is None:
                    continue
                failure_a.append(bool(_failure(left_events[key], challenge)))
                failure_b.append(bool(_failure(right_events[key], challenge)))

            if failure_a:
                set_a = {i for i, value in enumerate(failure_a) if value}
                set_b = {i for i, value in enumerate(failure_b) if value}
                union = set_a | set_b
                jaccard = len(set_a & set_b) / len(union) if union else 0.0
                phi = _phi(failure_a, failure_b)
                shared_failures = len(set_a & set_b)
            else:
                jaccard = None
                phi = None
                shared_failures = 0

            rows.append(
                {
                    "left": left.id,
                    "right": right.id,
                    "overlap": len(shared),
                    "agreement_rate": agreement,
                    "failure_jaccard": jaccard,
                    "failure_phi": phi,
                    "shared_failures": shared_failures,
                }
            )
    return rows


def challenge_metrics(
    challenges: list[Challenge], observations: list[Observation]
) -> dict[str, dict]:
    challenge_map = {item.id: item for item in challenges}
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.challenge_id].append(observation)

    result: dict[str, dict] = {}
    for challenge_id, items in sorted(grouped.items()):
        challenge = challenge_map.get(challenge_id)
        if challenge is None:
            continue
        counts = Counter(item.outcome.value for item in items)
        failures = [
            _failure(item, challenge)
            for item in items
            if challenge.expected is not None
        ]
        known_failures = [value for value in failures if value is not None]
        result[challenge_id] = {
            "family": challenge.family,
            "executions": len(items),
            "expected": challenge.expected.value if challenge.expected else None,
            "accept": counts[Outcome.ACCEPT.value],
            "reject": counts[Outcome.REJECT.value],
            "undetermined": counts[Outcome.UNDETERMINED.value],
            "error": counts[Outcome.ERROR.value],
            "timeout": counts[Outcome.TIMEOUT.value],
            "failure_rate": (
                sum(bool(value) for value in known_failures) / len(known_failures)
                if known_failures
                else None
            ),
        }
    return result
