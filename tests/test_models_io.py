import json
from pathlib import Path

import pytest

from cogent.errors import ConfigError
from cogent.io import load_corpus, load_fleet, load_observations
from cogent.models import Outcome


ROOT = Path(__file__).resolve().parents[1]


def test_load_example_fleet():
    fleet = load_fleet(ROOT / "examples" / "fleet.yaml")
    assert len(fleet) == 7
    assert fleet[0].id == "alpha-1"
    assert fleet[0].stake == 10


def test_load_default_corpus():
    corpus = load_corpus(ROOT / "corpus" / "default.yaml")
    assert len(corpus) == 12
    assert {item.family for item in corpus} >= {"source-conflict", "prompt-injection"}


def test_outcome_is_case_insensitive():
    assert Outcome.parse("accept") is Outcome.ACCEPT


def test_duplicate_validator_id_is_rejected(tmp_path):
    path = tmp_path / "fleet.json"
    path.write_text(json.dumps({"validators": [{"id": "x"}, {"id": "x"}]}))
    with pytest.raises(ConfigError, match="unique"):
        load_fleet(path)


def test_invalid_challenge_expected_rejected(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"challenges": [{"id": "c", "family": "f", "expected": "MAYBE"}]}))
    with pytest.raises(ConfigError):
        load_corpus(path)


def test_jsonl_observations(tmp_path):
    path = tmp_path / "obs.jsonl"
    path.write_text('{"validator_id":"v","challenge_id":"c","run_id":"0","outcome":"ACCEPT"}\n')
    observations = load_observations(path)
    assert observations[0].outcome is Outcome.ACCEPT
