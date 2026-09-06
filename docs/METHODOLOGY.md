# Methodology and claim boundaries

Cogent measures **empirical behavioral independence**. This document is intentionally conservative
about interpretation.

## Unit of observation

One observation is one validator's result on one challenge execution (`challenge_id`, `run_id`). The
allowed outcomes are `ACCEPT`, `REJECT`, `UNDETERMINED`, `TIMEOUT`, and `ERROR`.

When a challenge declares an expected outcome, any non-matching outcome is a failure. Operational
outcomes are also reported separately so model disagreement and infrastructure health are not hidden
inside one score.

## Pairwise measurements

Outcome agreement is the fraction of shared events with equal outcomes.

Co-failure Jaccard compares only the events where either member failed. A high value means the pair
fails on many of the same labeled cases.

Phi correlation is calculated over binary fail/pass vectors. Cogent ignores negative phi for clustering
because the target question is correlated failure, not complementary behavior.

## Cluster rule

Validators are connected when:

1. they share at least `min_shared_failures`; and
2. `max(co_failure_jaccard, positive_phi) >= cluster_threshold`.

Connected components form clusters. This is an empirical grouping, not a statement about common
ownership, provider identity, collusion, or causal dependence.

## Effective failure-domain count

Each empirical cluster is assigned the sum of member stake weights. If cluster stake shares are
`p_1 ... p_n`, Cogent reports:

`effective_failure_domains = 1 / sum(p_i^2)`

It also reports `effective_failure_domains / nominal_validator_count` as normalized diversity.

This is a concentration statistic over the observed clusters only. It must not be described as a
Nakamoto coefficient.

## Committee simulation

Simulation uses weighted sampling without replacement with deterministic pseudo-randomness. For every
sample:

1. select a committee;
2. test whether one empirical cluster reaches ordinary majority;
3. choose one observed labeled challenge execution;
4. replay the selected validators' recorded binary votes;
5. report expected majority, wrong majority, or undetermined.

Samples with missing selected-validator observations for the chosen event are skipped from vote-outcome
rates but still count for cluster-majority risk.

## Appropriate claims

Good:

- "On corpus v3, validators A/B/C shared 82% of their failure cases."
- "Under the supplied stake weights, 18% of simulated 5-validator committees contained a majority from
  one empirical failure cluster."
- "Validator X's failure rate rose by 4.2 percentage points on matching challenge executions."

Bad:

- "GenLayer is 82% decentralized."
- "There is an 18% chance live consensus will fail."
- "Validators A/B/C are the same operator."
- "Validator X is malicious."

## Corpus quality

Cogent is only as meaningful as its challenge mapping and expected labels. Projects should version
corpora, document why expected outcomes are defensible, preserve minimized real-world regressions, and
run repeated executions when stochasticity matters.
