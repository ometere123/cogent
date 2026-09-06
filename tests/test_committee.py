from cogent.committee import simulate_committees
from cogent.models import Challenge, Observation, Outcome, ValidatorProfile


def _dataset():
    validators = [ValidatorProfile(str(i), stake=1) for i in range(5)]
    challenges = [Challenge("c", "f", "", Outcome.ACCEPT)]
    observations = [
        Observation("0", "c", "0", Outcome.REJECT),
        Observation("1", "c", "0", Outcome.REJECT),
        Observation("2", "c", "0", Outcome.REJECT),
        Observation("3", "c", "0", Outcome.ACCEPT),
        Observation("4", "c", "0", Outcome.ACCEPT),
    ]
    clusters = [
        {"id": "C1", "validators": ["0", "1", "2"], "size": 3},
        {"id": "C2", "validators": ["3"], "size": 1},
        {"id": "C3", "validators": ["4"], "size": 1},
    ]
    return validators, challenges, observations, clusters


def test_committee_simulation_is_deterministic():
    args = _dataset()
    a = simulate_committees(*args, committee_size=3, simulations=1000, seed=42)
    b = simulate_committees(*args, committee_size=3, simulations=1000, seed=42)
    assert a == b


def test_committee_simulation_has_empirical_rates():
    result = simulate_committees(*_dataset(), committee_size=3, simulations=1000, seed=1)
    assert 0 <= result["correlated_cluster_majority_rate"] <= 1
    assert 0 <= result["wrong_majority_rate"] <= 1
    assert result["evaluated_consensus_samples"] == 1000
