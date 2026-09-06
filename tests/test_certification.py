from cogent.certification import certify_validator


def test_certification_policy_passes():
    analysis = {
        "validators": {"v": {"failure_rate": 0.01, "operational_failure_rate": 0.0}},
        "clusters": [{"id": "C1", "validators": ["v"], "size": 1}],
    }
    result = certify_validator(analysis, "v", max_failure_rate=0.05, max_cluster_size=1)
    assert result["passed"] is True


def test_certification_policy_fails():
    analysis = {
        "validators": {"v": {"failure_rate": 0.2, "operational_failure_rate": 0.0}},
        "clusters": [{"id": "C1", "validators": ["v"], "size": 3}],
    }
    result = certify_validator(analysis, "v", max_failure_rate=0.05, max_cluster_size=2)
    assert result["passed"] is False
