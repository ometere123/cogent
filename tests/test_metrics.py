from cogent.metrics import challenge_metrics, pairwise_metrics, validator_metrics
from cogent.models import Challenge, Observation, Outcome, ValidatorProfile


def _fixtures():
    validators = [ValidatorProfile("a"), ValidatorProfile("b"), ValidatorProfile("c")]
    challenges = [
        Challenge("x", "fam", "", Outcome.ACCEPT),
        Challenge("y", "fam", "", Outcome.REJECT),
        Challenge("z", "fam2", "", Outcome.ACCEPT),
    ]
    observations = [
        Observation("a", "x", "0", Outcome.REJECT),
        Observation("b", "x", "0", Outcome.REJECT),
        Observation("c", "x", "0", Outcome.ACCEPT),
        Observation("a", "y", "0", Outcome.ACCEPT),
        Observation("b", "y", "0", Outcome.ACCEPT),
        Observation("c", "y", "0", Outcome.REJECT),
        Observation("a", "z", "0", Outcome.ACCEPT),
        Observation("b", "z", "0", Outcome.ACCEPT),
        Observation("c", "z", "0", Outcome.ACCEPT),
    ]
    return validators, challenges, observations


def test_validator_failure_rate():
    validators, challenges, observations = _fixtures()
    metrics = validator_metrics(validators, challenges, observations)
    assert metrics["a"]["failure_rate"] == 2 / 3
    assert metrics["c"]["failure_rate"] == 0


def test_pairwise_cofailure_detects_pair():
    validators, challenges, observations = _fixtures()
    rows = pairwise_metrics(validators, challenges, observations)
    ab = next(row for row in rows if row["left"] == "a" and row["right"] == "b")
    assert ab["failure_jaccard"] == 1.0
    assert ab["shared_failures"] == 2


def test_pairwise_independent_validator_has_zero_shared_failures():
    validators, challenges, observations = _fixtures()
    rows = pairwise_metrics(validators, challenges, observations)
    ac = next(row for row in rows if row["left"] == "a" and row["right"] == "c")
    assert ac["shared_failures"] == 0


def test_challenge_failure_rate():
    validators, challenges, observations = _fixtures()
    metrics = challenge_metrics(challenges, observations)
    assert metrics["x"]["failure_rate"] == 2 / 3
