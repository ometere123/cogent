from cogent.drift import drift_report
from cogent.models import Challenge, Observation, Outcome


def test_drift_detects_behavior_change():
    challenges = [Challenge("c", "f", "", Outcome.ACCEPT)]
    baseline = [Observation("v", "c", "0", Outcome.ACCEPT)]
    current = [Observation("v", "c", "0", Outcome.REJECT)]
    result = drift_report(challenges, baseline, current)
    metrics = result["validators"]["v"]
    assert metrics["behavior_change_rate"] == 1.0
    assert metrics["failure_rate_delta"] == 1.0


def test_drift_tracks_unmatched_events():
    challenges = [Challenge("c", "f", "", Outcome.ACCEPT)]
    baseline = [Observation("v", "c", "0", Outcome.ACCEPT)]
    current = [Observation("v", "c", "1", Outcome.ACCEPT)]
    result = drift_report(challenges, baseline, current)
    assert result["shared_events"] == 0
    assert result["baseline_only_events"] == 1
    assert result["current_only_events"] == 1
