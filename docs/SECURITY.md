# Security model

## Secret handling

Cogent profiles should reference provider secrets by environment-variable **name**, not embed secret
values. Public transaction-context exports recursively redact keys containing common secret/token/key
fragments, except fields explicitly denoting environment-variable names.

The external runner inherits the current environment so existing `genlayer-test` or provider setup can
work. This means a malicious runner can access the same credentials as any other local process. Only
execute trusted runners.

## Report integrity

Cogent reports are measurement artifacts, not signed attestations. Preserve the exact fleet, corpus,
observations, Cogent version, and CI commit if a report will be used for release decisions.

## Statistical misuse

Do not treat a Cogent cluster as evidence of common ownership, collusion, or malicious behavior.
Correlated failures can arise from shared models, shared training data, similar prompts, source
availability, identical contract logic, or chance.

## Denial of service

Runner concurrency is user-controlled. Real LLM/Studio executions can be expensive or rate-limited.
Start with low `--workers` and bounded `--timeout`; use a deliberate challenge corpus rather than
unbounded fuzzing.

## Responsible disclosure

If a challenge reveals a consensus-safety weakness in a third-party contract, disclose it to the
maintainer before publishing an exploitable reproduction when appropriate.
