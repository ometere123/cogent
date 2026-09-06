import json
from pathlib import Path

import pytest

from cogent.direct import load_direct_lab, run_direct_matrix
from cogent.errors import ConfigError
from cogent.models import Challenge, Outcome, ValidatorProfile

CONTRACT_SOURCE = '''# v0.1.0
# { "Depends": "py-genlayer:latest" }

import genlayer as gl


class EvidenceGate(gl.Contract):
    result: str

    def __init__(self):
        self.result = ""

    @gl.public.write
    def judge(self, url: str) -> None:
        def leader_fn():
            response = gl.nondet.web.get(url)
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")
            return response.body.decode("utf-8")

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            response = gl.nondet.web.get(url)
            if response.status != 200:
                return False
            return leaders_res.calldata == response.body.decode("utf-8")

        self.result = gl.vm.run_nondet(leader_fn, validator_fn)
'''


def _write_lab(tmp_path: Path, *, include_unknown_validator: bool = False) -> tuple[Path, Path]:
    contract_path = tmp_path / "EvidenceGate.py"
    contract_path.write_text(CONTRACT_SOURCE, encoding="utf-8")

    validator_overrides = {
        "validator-b": {
            "web": [
                {
                    "pattern": r"evidence\.example/data",
                    "status": 200,
                    "body": json.dumps({"decision": "REJECT"}),
                }
            ]
        }
    }
    if include_unknown_validator:
        validator_overrides["not-in-fleet"] = {}

    lab = {
        "version": 1,
        "project_root": ".",
        "contract": {
            "path": contract_path.name,
            "sender": "cogent-native-test",
            "sdk_version": "v0.2.16",
        },
        "cases": {
            "source-conflict": {
                "method": "judge",
                "args": ["https://evidence.example/data"],
                "expected_captures": 1,
                "leader": {
                    "web": [
                        {
                            "pattern": r"evidence\.example/data",
                            "status": 200,
                            "body": json.dumps({"decision": "APPROVE"}),
                        }
                    ]
                },
                "validator": {
                    "web": [
                        {
                            "pattern": r"evidence\.example/data",
                            "status": 200,
                            "body": json.dumps({"decision": "APPROVE"}),
                        }
                    ]
                },
                "validators": validator_overrides,
            }
        },
    }
    lab_path = tmp_path / "direct-lab.json"
    lab_path.write_text(json.dumps(lab), encoding="utf-8")
    return contract_path, lab_path


def _fleet() -> list[ValidatorProfile]:
    return [ValidatorProfile("validator-a"), ValidatorProfile("validator-b")]


def _corpus() -> list[Challenge]:
    return [
        Challenge(
            id="source-conflict",
            family="source-conflict",
            description="validator-b receives evidence contradicting the leader",
            expected=Outcome.REJECT,
        )
    ]


def test_direct_lab_rejects_unknown_validator_override(tmp_path):
    _, lab_path = _write_lab(tmp_path, include_unknown_validator=True)
    with pytest.raises(ConfigError, match="unknown fleet ids"):
        load_direct_lab(lab_path, _fleet(), _corpus())


def test_native_direct_engine_executes_real_validator_fn(tmp_path):
    _, lab_path = _write_lab(tmp_path)
    observations = run_direct_matrix(_fleet(), _corpus(), lab_path)
    diagnostics = [
        {
            "validator": item.validator_id,
            "outcome": item.outcome.value,
            "reason": item.reason,
            "metadata": item.metadata,
        }
        for item in observations
    ]

    assert [(item.validator_id, item.outcome) for item in observations] == [
        ("validator-a", Outcome.ACCEPT),
        ("validator-b", Outcome.REJECT),
    ], diagnostics
    assert all(item.metadata["engine"] == "genlayer-test-direct" for item in observations)
    assert all(item.metadata["captured_nondet_blocks"] == 1 for item in observations)
    assert observations[0].metadata["validator_results"] == [True]
    assert observations[1].metadata["validator_results"] == [False]


def test_native_direct_engine_repetition_ids_are_stable(tmp_path):
    _, lab_path = _write_lab(tmp_path)
    observations = run_direct_matrix(_fleet(), _corpus(), lab_path, repetitions=2)

    keys = [(item.validator_id, item.challenge_id, item.run_id) for item in observations]
    assert keys == [
        ("validator-a", "source-conflict", "0"),
        ("validator-a", "source-conflict", "1"),
        ("validator-b", "source-conflict", "0"),
        ("validator-b", "source-conflict", "1"),
    ]
