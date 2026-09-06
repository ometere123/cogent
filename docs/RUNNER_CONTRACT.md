# External runner contract

Cogent intentionally does not hard-code how to call an arbitrary Intelligent Contract. `cogent run`
therefore starts an external executable for each validator/challenge/repetition job.

## Inputs

The runner receives these environment variables:

- `COGENT_CHALLENGE_FILE`: JSON challenge object.
- `COGENT_VALIDATOR_FILE`: JSON validator profile.
- `COGENT_TRANSACTION_CONTEXT_FILE`: JSON object compatible with the documented non-mocked
  `genlayer-test` validator transaction-context shape.
- `COGENT_RUN_ID`: repetition index.
- `COGENT_SEED`: deterministic 64-bit integer derived from global seed + validator + challenge + run.

The runner should map the generic challenge payload to the target project's actual test setup. For
example, a `source-conflict` challenge may select mocked web bodies; a `leader-bias` challenge may
configure leader and validator LLM responses; a temporal challenge may pin `genvm_datetime`.

## Output

The runner may print logs, but its final non-empty stdout line must be one JSON object:

```json
{
  "outcome": "ACCEPT",
  "reason": "optional explanation",
  "latency_ms": 1234.5,
  "metadata": {
    "optional": "machine-readable project evidence"
  }
}
```

Allowed outcomes:

- `ACCEPT`
- `REJECT`
- `UNDETERMINED`
- `TIMEOUT`
- `ERROR`

A successful runner process exits `0`, even when the *validator outcome* is `REJECT` or
`UNDETERMINED`. Process failure is infrastructure failure and Cogent records it as `ERROR`. Process
timeout is recorded as `TIMEOUT`.

## Security

The runner is arbitrary code supplied by the developer. Cogent executes it directly without a shell,
but it inherits the current process environment so that normal GenLayer/LLM credentials remain
available to the project's own harness. Never use untrusted runner commands.

Cogent does not copy environment values into its report. The temporary runner JSON files are deleted
when the job exits.
