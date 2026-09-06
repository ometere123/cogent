from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from .models import Challenge, Observation, Outcome


def _failure(outcome: Outcome, expected: Outcome | None) -> bool | None:
    if expected is None:
        return None
    if outcome in (Outcome.ERROR, Outcome.TIMEOUT, Outcome.UNDETERMINED):
        return True
    return outcome != expected


def drift_report(
    challenges: list[Challenge],
    baseline: list[Observation],
    current: list[Observation],
) -> dict:
    challenge_map = {item.id: item for item in challenges}
    old = {(o.validator_id, o.challenge_id, o.run_id): o for o in baseline}
    new = {(o.validator_id, o.challenge_id, o.run_id): o for o in current}
    shared = sorted(set(old) & set(new))
    per_validator: dict[str, dict[str, float | int | None]] = {}
    grouped: dict[str, list[tuple]] = defaultdict(list)
    for key in shared:
        grouped[key[0]].append(key)

    for validator_id, keys in sorted(grouped.items()):
        changed = sum(old[key].outcome != new[key].outcome for key in keys)
        old_failures = []
        new_failures = []
        for key in keys:
            challenge = challenge_map.get(key[1])
            expected = challenge.expected if challenge else None
            a = _failure(old[key].outcome, expected)
            b = _failure(new[key].outcome, expected)
            if a is not None:
                old_failures.append(a)
                new_failures.append(bool(b))
        old_rate = sum(old_failures) / len(old_failures) if old_failures else None
        new_rate = sum(new_failures) / len(new_failures) if new_failures else None
        per_validator[validator_id] = {
            "shared_events": len(keys),
            "changed_events": changed,
            "behavior_change_rate": changed / len(keys) if keys else 0.0,
            "baseline_failure_rate": old_rate,
            "current_failure_rate": new_rate,
            "failure_rate_delta": (
                new_rate - old_rate if old_rate is not None and new_rate is not None else None
            ),
        }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "shared_events": len(shared),
        "baseline_only_events": len(set(old) - set(new)),
        "current_only_events": len(set(new) - set(old)),
        "validators": per_validator,
        "scope_warning": "Drift is measured only on matching validator/challenge/run observations.",
    }
