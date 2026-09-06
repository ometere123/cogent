import json
import subprocess
import sys
from pathlib import Path

import yaml

from cogent.analysis import AnalysisConfig, analyze
from cogent.io import load_corpus, load_fleet
from cogent.reporting import analysis_markdown
from cogent.runner import run_matrix

ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_end_to_end():
    validators = load_fleet(ROOT / "examples" / "fleet.yaml")[:4]
    challenges = load_corpus(ROOT / "corpus" / "default.yaml")[:4]
    observations = run_matrix(
        f"{sys.executable} {ROOT / 'examples' / 'runner_synthetic.py'}",
        validators,
        challenges,
        repetitions=1,
        workers=4,
    )
    result = analyze(
        validators,
        challenges,
        observations,
        AnalysisConfig(committee_size=3, simulations=200, seed=3, min_shared_failures=2),
    )
    assert result["fleet"]["validators"] == 4
    assert result["corpus"]["observations"] == 16
    assert len(result["clusters"]) >= 2
    assert "Cogent behavioral-independence report" in analysis_markdown(result)


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "cogent", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "committee-risk" in result.stdout


def test_cli_full_demo(tmp_path):
    fleet_data = {
        "validators": [
            {"id": "a", "stake": 1, "labels": {"synthetic_behavior": "alpha"}},
            {"id": "b", "stake": 1, "labels": {"synthetic_behavior": "delta"}},
            {"id": "c", "stake": 1, "labels": {"synthetic_behavior": "gamma"}},
        ]
    }
    corpus_data = {
        "challenges": [
            {"id": "x", "family": "source-conflict", "description": "x", "expected": "REJECT"},
            {"id": "y", "family": "semantic-equivalence", "description": "y", "expected": "ACCEPT"},
        ]
    }
    fleet = tmp_path / "fleet.yaml"
    corpus = tmp_path / "corpus.yaml"
    fleet.write_text(yaml.safe_dump(fleet_data))
    corpus.write_text(yaml.safe_dump(corpus_data))
    observations = tmp_path / "obs.jsonl"
    report = tmp_path / "report"
    run = subprocess.run(
        [
            sys.executable, "-m", "cogent", "run",
            "--fleet", str(fleet),
            "--corpus", str(corpus),
            "--runner", f"{sys.executable} {ROOT / 'examples' / 'runner_synthetic.py'}",
            "--workers", "3",
            "--output", str(observations),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    analyzed = subprocess.run(
        [
            sys.executable, "-m", "cogent", "analyze",
            "--fleet", str(fleet),
            "--corpus", str(corpus),
            "--observations", str(observations),
            "--committee-size", "3",
            "--output-dir", str(report),
            "--simulations", "100",
            "--min-shared-failures", "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert analyzed.returncode == 0, analyzed.stderr
    data = json.loads((report / "analysis.json").read_text())
    assert data["schema_version"] == 1
    assert (report / "report.md").exists()


def test_cli_init_uses_packaged_templates(tmp_path):
    target = tmp_path / "lab"
    result = subprocess.run(
        [sys.executable, "-m", "cogent", "init", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (target / "fleet.yaml").exists()
    assert (target / "corpus.yaml").exists()
    assert (target / "runner.py").exists()
