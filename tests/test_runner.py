import sys

from cogent.models import Challenge, Outcome, ValidatorProfile
from cogent.runner import derived_seed, run_matrix


def test_derived_seed_is_stable_and_specific():
    a = derived_seed(7, "v", "c", 0)
    b = derived_seed(7, "v", "c", 0)
    c = derived_seed(7, "v", "c", 1)
    assert a == b
    assert a != c


def test_runner_executes_external_protocol(tmp_path):
    script = tmp_path / "runner.py"
    script.write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "c=json.loads(Path(os.environ['COGENT_CHALLENGE_FILE']).read_text())\n"
        "print(json.dumps({'outcome': c['expected'], 'metadata': {'ok': True}}))\n"
    )
    observations = run_matrix(
        f"{sys.executable} {script}",
        [ValidatorProfile("v")],
        [Challenge("c", "f", "", Outcome.ACCEPT)],
        repetitions=2,
    )
    assert [item.outcome for item in observations] == [Outcome.ACCEPT, Outcome.ACCEPT]
    assert all(item.metadata["ok"] for item in observations)


def test_runner_nonzero_exit_becomes_error(tmp_path):
    script = tmp_path / "bad.py"
    script.write_text("raise SystemExit(9)\n")
    observations = run_matrix(
        f"{sys.executable} {script}",
        [ValidatorProfile("v")],
        [Challenge("c", "f", "", Outcome.ACCEPT)],
    )
    assert observations[0].outcome is Outcome.ERROR
