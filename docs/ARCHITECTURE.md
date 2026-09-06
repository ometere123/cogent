# Architecture

Cogent is intentionally split into an execution plane and an analysis plane.

## Execution plane

`cogent run` enumerates `(challenge, validator, repetition)` jobs. For every job it writes three
short-lived JSON files: the challenge, validator profile, and a GenLayer transaction context. It then
starts a developer-supplied executable with file locations and a deterministic seed in environment
variables.

This boundary makes Cogent:

1. contract-agnostic — it does not need to know a project's method names or storage schema;
2. runner-agnostic — `genlayer-test`, local Studio RPC, or a custom harness can be used;
3. language-agnostic — the runner only needs to read JSON and emit JSON;
4. auditable — the exact behavioral observations are stored as JSONL and can be re-analyzed offline.

Cogent does not inject or read browser wallets. Network signers, if a specific integration test needs
one, remain the responsibility of the developer's runner and normal GenLayer tooling.

## Analysis plane

The analysis engine consumes immutable observations and produces:

- per-validator metrics;
- per-challenge metrics;
- pairwise behavioral metrics;
- empirical co-failure clusters;
- stake-weighted diversity concentration;
- committee-risk simulations.

Because the analysis works from saved observations, a reviewer can reproduce the report without LLM
keys or network access.

## Why not infer clusters from provider/model labels?

Provider/model metadata is useful context but is not treated as ground truth about independence. Two
validators with different labels can fail identically, while two validators sharing a provider may
behave differently due to model, configuration, prompt, plugin, or future provider changes. Cogent
therefore clusters from observed co-failure behavior.

## Why union-find clustering?

The first release uses a deliberately interpretable threshold graph instead of an opaque ML clustering
pipeline. An edge exists only when two validators have at least `min_shared_failures` and their
co-failure Jaccard or positive phi reaches `cluster_threshold`. Connected components become empirical
failure clusters.

This makes every cluster explainable from pairwise rows in `analysis.json` and prevents a statistical
package upgrade from silently changing semantics.

## Committee simulation

Validator sampling uses weighted sampling without replacement. The simulation is reproducible with a
seed and never claims to reproduce the live protocol's full committee-selection implementation. It is
an engineering risk model over supplied stake weights and observations.

See `docs/METHODOLOGY.md` for formulas and claim boundaries.
