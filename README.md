# Cogent

**Behavioral decentralization and correlated-failure infrastructure for GenLayer validators.**

Cogent measures whether a validator fleet behaves like independent judgment or like a smaller number
of correlated cognitive failure domains. It is deliberately **not** an Intelligent Contract, dapp,
wallet flow, or generic LLM benchmark. Developers bring their own GenLayer contracts, validator
profiles, and challenge mappings; Cogent orchestrates experiments and turns validator outcomes into
reproducible engineering evidence.

> **Claim boundary:** Cogent reports empirical behavior on a declared challenge corpus. It does not
> claim to prove validator honesty, protocol-wide decentralization, future model behavior, or the
> probability of a live consensus outcome.

## Why this exists

GenLayer validators can use different LLM providers, models, configurations, and plugins. The official
`genlayer-test` suite already supports custom validator contexts and multi-validator testing. That makes
an additional question measurable:

> If nominally different validators face the same adversarial equivalence-principle cases, do they fail
> independently, or do they fail together?

Traditional node health checks answer whether a validator can reach consensus infrastructure, GenVM,
and its configured LLM provider. Cogent targets a different layer: **behavioral independence under the
actual decision patterns GenLayer contracts depend on.**

## What Cogent does

- Defines portable, versioned challenge corpora for GenLayer validator behavior.
- Models GenLayer validator profiles using the same provider/model/config/plugin fields used by
  `genlayer-test` transaction contexts.
- Runs a validator × challenge × repetition matrix through a language-agnostic external runner.
- Records `ACCEPT`, `REJECT`, `UNDETERMINED`, `TIMEOUT`, and `ERROR` observations as JSONL.
- Computes per-validator failure and operational reliability metrics.
- Measures pairwise outcome agreement, co-failure Jaccard similarity, and failure phi correlation.
- Clusters validators only when there is enough shared failure evidence.
- Estimates an **effective empirical failure-domain count** using stake-weighted cluster concentration.
- Simulates stake-weighted committee selection over the observed corpus.
- Reports same-cluster-majority, wrong-majority, correct-majority, and undetermined rates.
- Compares two runs for validator behavioral drift.
- Applies local readiness thresholds for CI or validator admission checks.
- Exports redacted `genlayer-test`-compatible validator transaction contexts.
- Never writes environment-secret values into its public report artifacts.

## What Cogent does not do

- It does not deploy or own an Intelligent Contract.
- It does not need a frontend or browser wallet.
- It does not replace `genlayer-test`, GenLayer Studio, GenVM, or node monitoring.
- It does not infer a validator's provider from behavior.
- It does not call correlated behavior malicious or dishonest.
- It does not turn a benchmark score into a protocol guarantee.

## Architecture

```text
                         your GenLayer project
                                 |
                +----------------+----------------+
                |                                 |
          fleet.yaml                         corpus.yaml
                |                                 |
                +---------------+-----------------+
                                |
                         cogent run
                                |
                   external runner boundary
                                |
             +------------------+------------------+
             |                                     |
       genlayer-test / Studio                any custom harness
       transaction_context                  that returns outcome
             |                                     |
             +------------------+------------------+
                                |
                     observations.jsonl
                                |
          +---------------------+---------------------+
          |                     |                     |
      metrics             failure clusters      committee sim
          |                     |                     |
          +---------------------+---------------------+
                                |
                    analysis.json + report.md
                                |
                 drift / certify / CI thresholds
```

The runner boundary is intentional. Cogent cannot know how a project's contract maps a generic
`source-conflict` or `prompt-injection` challenge into that contract's mocked web evidence, leader
proposal, method arguments, or expected equivalence-principle behavior. The project-specific runner
owns that mapping; Cogent owns orchestration and analysis.

## Installation

Python 3.12+:

```bash
pip install -e .
```

For development:

```bash
pip install -e '.[dev]'
pytest
```

To round-trip validator profiles through the installed GenLayer testing suite:

```bash
pip install -e '.[genlayer]'
cogent validate --fleet fleet.yaml --corpus corpus.yaml --gltest
```

## Five-minute demo

The included synthetic runner exists only to demonstrate the infrastructure without requiring network
credentials or an example Intelligent Contract.

```bash
cogent run \
  --fleet examples/fleet.yaml \
  --corpus corpus/default.yaml \
  --runner 'python examples/runner_synthetic.py' \
  --repetitions 3 \
  --workers 4 \
  --output demo-observations.jsonl

cogent analyze \
  --fleet examples/fleet.yaml \
  --corpus corpus/default.yaml \
  --observations demo-observations.jsonl \
  --committee-size 5 \
  --simulations 10000 \
  --output-dir demo-report
```

The output directory contains:

```text
demo-report/
  analysis.json   # machine-readable measurements
  report.md       # reviewer/operator-readable report
```

## Real GenLayer integration

`genlayer-test` accepts custom validator descriptions through `transaction_context`. Cogent fleet
profiles mirror the relevant fields:

```yaml
validators:
  - id: validator-a
    stake: 10
    provider: openai
    model: gpt-4o
    plugin: openai-compatible
    config:
      temperature: 0.2
    plugin_config:
      api_key_env_var: OPENAI_API_KEY
```

Export a fleet context:

```bash
cogent contexts \
  --fleet examples/fleet.yaml \
  --output transaction-context.json
```

Or one context per validator:

```bash
cogent contexts \
  --fleet examples/fleet.yaml \
  --individual \
  --output validator-contexts.json
```

A real runner reads the files Cogent provides in its environment:

```text
COGENT_CHALLENGE_FILE
COGENT_VALIDATOR_FILE
COGENT_TRANSACTION_CONTEXT_FILE
COGENT_RUN_ID
COGENT_SEED
```

It then performs the project-specific `genlayer-test` / Studio execution and prints one final JSON line:

```json
{
  "outcome": "REJECT",
  "reason": "validator rejected the leader proposal after independent evidence retrieval",
  "metadata": {
    "tx_hash": "optional",
    "network": "localnet"
  }
}
```

The executable exits `0` when it successfully produced an observation. Cogent converts runner
process failures to `ERROR` and process timeouts to `TIMEOUT`, preserving them as behavioral evidence
instead of silently dropping them.

See [docs/RUNNER_CONTRACT.md](docs/RUNNER_CONTRACT.md) for a complete adapter contract and
[docs/GENLAYER_INTEGRATION.md](docs/GENLAYER_INTEGRATION.md) for `gltest` guidance.

## Challenge corpus

Cogent's default corpus intentionally describes **behavioral perturbations**, not one application's
business logic. Current families include:

- source conflict
- stale web evidence
- missing evidence / fail-closed behavior
- evidence prompt injection
- leader confidence bias
- semantic equivalence
- evidence ordering
- temporal ambiguity
- malformed evidence

Each project should extend or replace these with contract-specific cases and explicit expected
`ACCEPT`/`REJECT` labels wherever a defensible oracle exists. Unlabeled cases may still be used for
agreement/instability analysis but are excluded from failure-rate calculations.

## Metrics

### Validator failure rate

For challenges with a known expected validator outcome, `ERROR`, `TIMEOUT`, and `UNDETERMINED` are
counted as failures. Cogent also reports operational failures separately.

### Co-failure Jaccard

For two validators, Cogent compares the set of labeled challenge executions each got wrong:

```text
|failures(A) ∩ failures(B)|
---------------------------
|failures(A) ∪ failures(B)|
```

This answers whether two validators tend to fail on the same cases.

### Failure phi

Cogent also computes a phi coefficient over the pair's binary fail/pass vectors. Clustering uses the
stronger of positive phi and co-failure Jaccard, but only after a configurable minimum number of
shared failures. That minimum prevents one coincidental shared error from creating a "correlated"
cluster.

### Effective empirical failure domains

After clustering, Cogent calculates inverse-Simpson concentration over **stake share of the observed
failure clusters**:

```text
1 / sum(cluster_stake_share^2)
```

If every validator is a singleton empirical cluster, the value approaches the nominal validator count
(when stakes are similar). If stake is concentrated in one correlated cluster, it falls.

This metric is deliberately named an **effective empirical failure-domain count**, not a Nakamoto
coefficient and not a claim that validators in separate clusters are truly independent.

### Committee simulation

Cogent performs deterministic-seed Monte Carlo sampling with stake-weighted selection without
replacement. For each sampled committee it can replay one observed challenge event and calculate:

- whether a single empirical failure cluster forms a committee majority;
- whether observed votes produce the expected majority outcome;
- whether no binary outcome reaches majority (`UNDETERMINED`).

The simulation is conditional on the supplied fleet, stake weights, challenge corpus, and observed
behavior. The report embeds this scope warning.

## Drift

Repeat the same corpus after a model/provider/configuration change and compare runs:

```bash
cogent drift \
  --corpus corpus/default.yaml \
  --baseline september.jsonl \
  --current october.jsonl \
  --output drift.json
```

For each validator Cogent reports:

- shared events;
- outcome-change rate;
- baseline failure rate;
- current failure rate;
- failure-rate delta.

This is useful before changing a validator's model or plugin, after provider upgrades, and after a
contract modifies its equivalence-principle logic.

## CI policy

Cogent keeps measurement separate from policy. An organization chooses its own thresholds:

```bash
cogent ci \
  --analysis demo-report/analysis.json \
  --min-normalized-diversity 0.50 \
  --max-correlated-majority-rate 0.25 \
  --max-wrong-majority-rate 0.05
```

Exit codes:

- `0`: all configured checks pass;
- `3`: one or more CI policy checks fail;
- `2`: invalid input / execution error.

Validator-specific readiness policy:

```bash
cogent certify \
  --analysis demo-report/analysis.json \
  --validator delta-1 \
  --max-failure-rate 0.05 \
  --max-operational-failure-rate 0.02 \
  --max-cluster-size 2
```

"Certification" here is explicitly a local policy decision over an empirical run; it is not an
on-chain attestation or official GenLayer validator certification.

## Security and privacy

Cogent treats runner configuration as potentially sensitive:

- `plugin_config` should normally contain an environment variable name, not an API key value.
- Saved transaction-context exports redact fields whose names resemble secrets/tokens/passwords.
- Cogent never reads the value of `OPENAI_API_KEY` or another provider secret merely to render a report.
- External runners are arbitrary developer-supplied executables and therefore run with the developer's
  local permissions. Treat runner commands as code.
- Runner stderr stored in `ERROR` metadata is clipped to reduce accidental large log capture; projects
  should still avoid printing secrets.

See [docs/SECURITY.md](docs/SECURITY.md).

## Repository purity

There is intentionally no `contracts/` directory in this repository. Cogent is infrastructure for
**other people's GenLayer contracts and validators**. This avoids confusing the tool with a reusable
Intelligent Contract or a dapp that happens to have a CLI.

## Commands

```text
cogent init             create a starter lab
cogent validate         validate fleet/corpus/observations; optionally round-trip gltest profiles
cogent contexts         export GenLayer transaction contexts
cogent runner-contract  print the runner protocol
cogent run              execute validator × challenge experiments
cogent analyze          generate metrics, clusters, simulation, and Markdown report
cogent simulate         print committee-risk simulation only
cogent drift            compare two observation datasets
cogent certify          apply one validator readiness policy
cogent ci               enforce fleet-level CI thresholds
```

Run `cogent <command> --help` for complete arguments.

## GenLayer references

Cogent's integration model follows the current public GenLayer tooling surfaces:

- Testing Intelligent Contracts: https://docs.genlayer.com/developers/intelligent-contracts/testing
- `genlayer-test` API: https://docs.genlayer.com/api-references/genlayer-test
- Studio validators: https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-studio/validators
- Validator setup / GenVM diagnostics: https://docs.genlayer.com/validators/setup-guide
- GenLayer testing suite source: https://github.com/genlayerlabs/genlayer-testing-suite

## License

MIT. See [LICENSE](LICENSE).
