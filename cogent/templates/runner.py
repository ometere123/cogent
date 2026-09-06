"""Synthetic Cogent runner used only for smoke tests and demos.

A real project runner should use COGENT_TRANSACTION_CONTEXT_FILE with genlayer-test / Studio,
execute the target project's Intelligent Contract, and print one JSON result line.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path

challenge = json.loads(Path(os.environ["COGENT_CHALLENGE_FILE"]).read_text())
validator = json.loads(Path(os.environ["COGENT_VALIDATOR_FILE"]).read_text())
seed = int(os.environ["COGENT_SEED"])
rng = random.Random(seed)

expected = challenge.get("expected")
family = challenge["family"]
behavior = validator.get("labels", {}).get("synthetic_behavior", "independent")

# Deliberately correlated synthetic weaknesses so `cogent analyze` has something to discover.
weaknesses = {
    "alpha": {"source-conflict", "stale-web", "prompt-injection"},
    "beta": {"temporal-ambiguity", "malformed-evidence"},
    "gamma": {"leader-bias"},
    "delta": set(),
    "epsilon": {"ordering"},
}

outcome = expected or "ACCEPT"
if family in weaknesses.get(behavior, set()):
    outcome = "REJECT" if outcome == "ACCEPT" else "ACCEPT"

# Tiny deterministic noise demonstrates repeated-run support without making the demo random.
if rng.random() < 0.01:
    outcome = "UNDETERMINED"

print(json.dumps({
    "outcome": outcome,
    "reason": f"synthetic behavior={behavior}, family={family}",
    "metadata": {"synthetic": True}
}))
