from cogent.analysis import AnalysisConfig, analyze
from cogent.evidence import EvidenceRequirements
from cogent.models import Challenge, Observation, Outcome, ValidatorProfile


def test_zero_failures_cannot_establish_failure_domain_diversity():
    validators = [ValidatorProfile(f"v{index}") for index in range(5)]
    challenges = [Challenge(f"c{index}", "trivial", "", Outcome.ACCEPT) for index in range(20)]
    observations = [
        Observation(validator.id, challenge.id, "0", Outcome.ACCEPT)
        for validator in validators for challenge in challenges
    ]
    report = analyze(
        validators, challenges, observations,
        AnalysisConfig(evidence_requirements=EvidenceRequirements(min_informative_failures=1)),
    )
    assert report["evidence_sufficiency"]["status"] == "INSUFFICIENT"
    assert report["diversity"]["effective_failure_domains"] is None
    assert report["diversity"]["normalized_diversity"] is None


def test_sufficient_evidence_requires_every_exposed_threshold():
    validators = [ValidatorProfile("a"), ValidatorProfile("b")]
    challenges = [Challenge("c", "family", "", Outcome.ACCEPT)]
    observations = [
        Observation("a", "c", "0", Outcome.REJECT),
        Observation("b", "c", "0", Outcome.REJECT),
    ]
    report = analyze(
        validators, challenges, observations,
        AnalysisConfig(evidence_requirements=EvidenceRequirements(
            min_labelled_challenges=1, min_challenge_families=1,
            min_observed_labelled_challenges=1,
            min_observations_per_validator=1, min_overlapping_events_per_pair=1,
            min_informative_failures=1, min_repetitions_for_stochastic_engine=1,
        )),
    )
    assert report["evidence_sufficiency"]["status"] == "SUFFICIENT"
