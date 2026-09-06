import pytest

from cogent.clustering import build_clusters, diversity_metrics
from cogent.models import ValidatorProfile


def test_cluster_requires_minimum_shared_failures():
    validators = [ValidatorProfile("a"), ValidatorProfile("b")]
    pairwise = [{
        "left": "a", "right": "b", "failure_jaccard": 1.0, "failure_phi": 1.0,
        "shared_failures": 1,
    }]
    clusters = build_clusters(validators, pairwise, threshold=0.75, min_shared_failures=2)
    assert len(clusters) == 2


def test_cluster_correlated_pair():
    validators = [ValidatorProfile("a"), ValidatorProfile("b"), ValidatorProfile("c")]
    pairwise = [
        {"left": "a", "right": "b", "failure_jaccard": 0.9, "failure_phi": 0.8, "shared_failures": 3},
        {"left": "a", "right": "c", "failure_jaccard": 0.1, "failure_phi": 0.0, "shared_failures": 0},
        {"left": "b", "right": "c", "failure_jaccard": 0.1, "failure_phi": 0.0, "shared_failures": 0},
    ]
    clusters = build_clusters(validators, pairwise)
    assert clusters[0]["validators"] == ["a", "b"]
    assert clusters[1]["validators"] == ["c"]


def test_diversity_equal_singletons():
    validators = [ValidatorProfile("a", stake=1), ValidatorProfile("b", stake=1)]
    clusters = [{"id": "C1", "validators": ["a"], "size": 1}, {"id": "C2", "validators": ["b"], "size": 1}]
    result = diversity_metrics(validators, clusters)
    assert result["effective_failure_domains"] == pytest.approx(2.0)
    assert result["normalized_diversity"] == pytest.approx(1.0)


def test_diversity_collapsed_cluster():
    validators = [ValidatorProfile("a", stake=1), ValidatorProfile("b", stake=1)]
    clusters = [{"id": "C1", "validators": ["a", "b"], "size": 2}]
    result = diversity_metrics(validators, clusters)
    assert result["effective_failure_domains"] == pytest.approx(1.0)
    assert result["normalized_diversity"] == pytest.approx(0.5)
