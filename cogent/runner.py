from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .genlayer import public_transaction_context, transaction_context
from .models import Challenge, Observation, Outcome, ValidatorProfile


def derived_seed(global_seed: int, validator_id: str, challenge_id: str, repetition: int) -> int:
    payload = f"{global_seed}:{validator_id}:{challenge_id}:{repetition}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _parse_runner_output(
    stdout: str,
    *,
    validator: ValidatorProfile,
    challenge: Challenge,
    run_id: str,
    elapsed_ms: float,
) -> Observation:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        return Observation(
            validator.id,
            challenge.id,
            run_id,
            Outcome.ERROR,
            elapsed_ms,
            "runner produced no JSON output",
        )
    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError:
        return Observation(
            validator.id,
            challenge.id,
            run_id,
            Outcome.ERROR,
            elapsed_ms,
            "runner's last non-empty stdout line is not JSON",
            {"stdout_tail": lines[-1][-500:]},
        )
    outcome = Outcome.parse(data.get("outcome", "ERROR"))
    return Observation(
        validator_id=validator.id,
        challenge_id=challenge.id,
        run_id=run_id,
        outcome=outcome,
        latency_ms=float(data.get("latency_ms", elapsed_ms)),
        reason=str(data.get("reason", "")),
        metadata=dict(data.get("metadata") or {}),
    )


def run_one(
    command: str,
    validator: ValidatorProfile,
    challenge: Challenge,
    repetition: int,
    *,
    global_seed: int,
    timeout_seconds: float,
) -> Observation:
    seed = derived_seed(global_seed, validator.id, challenge.id, repetition)
    run_id = str(repetition)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="cogent-") as temp_dir:
        root = Path(temp_dir)
        challenge_file = root / "challenge.json"
        validator_file = root / "validator.json"
        context_file = root / "transaction-context.json"
        challenge_file.write_text(json.dumps(challenge.to_dict(), indent=2), encoding="utf-8")
        validator_file.write_text(json.dumps(validator.to_dict(), indent=2), encoding="utf-8")
        # The runner gets the real profile context. Saved Cogent reports redact secret-looking values.
        context_file.write_text(
            json.dumps(transaction_context([validator]), indent=2), encoding="utf-8"
        )
        env = os.environ.copy()
        env.update(
            {
                "COGENT_CHALLENGE_FILE": str(challenge_file),
                "COGENT_VALIDATOR_FILE": str(validator_file),
                "COGENT_TRANSACTION_CONTEXT_FILE": str(context_file),
                "COGENT_RUN_ID": run_id,
                "COGENT_SEED": str(seed),
            }
        )
        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - started) * 1000
            return Observation(
                validator.id,
                challenge.id,
                run_id,
                Outcome.TIMEOUT,
                elapsed,
                f"runner exceeded {timeout_seconds:g}s timeout",
            )
        elapsed = (time.perf_counter() - started) * 1000
        if result.returncode != 0:
            return Observation(
                validator.id,
                challenge.id,
                run_id,
                Outcome.ERROR,
                elapsed,
                f"runner exited with code {result.returncode}",
                {"stderr_tail": result.stderr[-1000:]},
            )
        return _parse_runner_output(
            result.stdout,
            validator=validator,
            challenge=challenge,
            run_id=run_id,
            elapsed_ms=elapsed,
        )


def run_matrix(
    command: str,
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    *,
    repetitions: int = 1,
    global_seed: int = 7,
    timeout_seconds: float = 120.0,
    workers: int = 1,
) -> list[Observation]:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    if workers <= 0:
        raise ValueError("workers must be positive")
    jobs = [
        (validator, challenge, repetition)
        for challenge in challenges
        for validator in validators
        for repetition in range(repetitions)
    ]
    observations: list[Observation] = []
    if workers == 1:
        for validator, challenge, repetition in jobs:
            observations.append(
                run_one(
                    command,
                    validator,
                    challenge,
                    repetition,
                    global_seed=global_seed,
                    timeout_seconds=timeout_seconds,
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    run_one,
                    command,
                    validator,
                    challenge,
                    repetition,
                    global_seed=global_seed,
                    timeout_seconds=timeout_seconds,
                ): (validator.id, challenge.id, repetition)
                for validator, challenge, repetition in jobs
            }
            for future in as_completed(futures):
                observations.append(future.result())
    observations.sort(key=lambda item: (item.challenge_id, item.validator_id, item.run_id))
    return observations


def runner_contract_example() -> dict:
    return {
        "environment": [
            "COGENT_CHALLENGE_FILE",
            "COGENT_VALIDATOR_FILE",
            "COGENT_TRANSACTION_CONTEXT_FILE",
            "COGENT_RUN_ID",
            "COGENT_SEED",
        ],
        "stdout": {
            "outcome": "ACCEPT|REJECT|UNDETERMINED|TIMEOUT|ERROR",
            "reason": "optional human-readable reason",
            "latency_ms": "optional number",
            "metadata": "optional JSON object",
        },
        "artifact_context_example": public_transaction_context([]),
    }
