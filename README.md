# Cogent

**Behavioral decentralization and correlated-failure infrastructure for GenLayer validators.**

Cogent helps Intelligent Contract developers and validator operators answer a question ordinary node
health checks cannot:

> When nominally different GenLayer validators face the same adversarial equivalence-principle cases,
> do they fail independently, or do they fail together?

Cogent is deliberately **pure tooling**. It does not deploy or own an Intelligent Contract, it has no
frontend, and it has no wallet flow. Developers bring their own GenLayer contracts, validator fleet
profiles and challenge corpora.

> **Claim boundary:** Cogent reports empirical behavior on a declared experiment. It does not prove
> validator honesty, protocol-wide decentralization, future model behavior, or the probability of a
> live GenLayer consensus outcome.

## v0.2: Cogent now executes GenLayer validator paths itself

The first Cogent release could orchestrate experiments through an external runner. That remains useful
for Studio/testnet/custom harnesses, but it left the actual GenLayer execution boundary outside Cogent.

v0.2 adds a native engine built on the official `genlayer-test` Direct Mode API:

```text
user's Intelligent Contract
        |
        v
Cogent native Direct engine
        |
        +--> deploy_contract(...)
        |
        +--> leader evidence / LLM mocks
        |
        +--> contract method executes gl.vm.run_nondet
        |
        +--> genlayer-test captures leader_result + validator_fn
        |
        +--> validator-specific evidence / LLM mocks
        |
        +--> VMContext.run_validator(...)
        |
        v
per-validator ACCEPT / REJECT observations
        |
        v
correlation, clusters, drift and committee-risk analysis
```

Cogent no longer has to trust a custom process to print `{"outcome":"REJECT"}` for reproducible
Direct Mode labs. The `ACCEPT`/`REJECT` result comes from the developer's captured GenLayer validator
function executed by `genlayer-test`.

See [Native GenLayer Direct Mode](docs/NATIVE_DIRECT_MODE.md).

## Why this exists

GenLayer consensus adds a dimension traditional blockchain tooling does not measure: **independence of
judgment**. Five validators can be independent keys/operators while still sharing a cognitive failure
mode on stale evidence, prompt injection, temporal ambiguity, source conflict or leader bias.

Cogent measures that behavior without pretending the measurement is a protocol theorem.

## What Cogent does

- Executes user Intelligent Contracts through official `genlayer-test` Direct Mode.
- Captures real `gl.vm.run_nondet` validator functions after leader execution.
- Replays those validator functions with default or per-validator evidence/LLM mocks.
- Supports multiple captured nondeterministic blocks per contract method.
- Preserves an external-runner engine for Studio, Studionet and custom/live-provider experiments.
- Defines portable, versioned challenge corpora for GenLayer validator behavior.
- Models validator fleet profiles with GenLayer provider/model/config/plugin fields.
- Records `ACCEPT`, `REJECT`, `UNDETERMINED`, `TIMEOUT`, and `ERROR` observations as JSONL.
- Computes per-validator failure and operational reliability metrics.
- Measures pairwise outcome agreement, co-failure Jaccard similarity, and failure phi correlation.
- Builds empirical correlated-failure clusters with a minimum shared-failure threshold.
- Estimates an effective empirical failure-domain count from stake-weighted cluster concentration.
- Simulates committee risk over observed behavior.
- Compares experiment runs for validator behavioral drift.
- Applies local readiness thresholds for CI or validator-admission workflows.
- Exports redacted `genlayer-test`-compatible transaction contexts.
- Validates native lab manifests against a published JSON Schema.
- Never reads provider secret values merely to generate reports.

## What Cogent does not do

- It does not deploy or own an Intelligent Contract.
- It does not need a frontend or browser wallet.
- It does not replace `genlayer-test`, GenLayer Studio, GenVM or node monitoring.
- Direct Mode does not claim full Studio/network fidelity.
- Mock-backed Direct Mode does not claim to benchmark a named production LLM model.
- Cogent does not infer providers from behavior.
- Correlated behavior is not labeled malicious or dishonest.
- Empirical committee-risk numbers are not protocol guarantees.

## Installation

Python 3.12+:

```bash
pip install -e .
```

For Cogent development:

```bash
pip install -e '.[dev]'
pytest
```

For native GenLayer Direct Mode and official validator-profile round trips:

```bash
pip install -e '.[genlayer]'
```

Cogent v0.2 is aligned to the current `genlayer-test` 0.29.x family.

## Native Direct Mode

### 1. Define a focused challenge corpus

```yaml
version: 1
name: permit-consensus-cases
challenges:
  - id: authoritative-source-contradicts-leader
    family: source-conflict
    description: Leader accepts while the authoritative source contradicts it.
    expected: REJECT
```

### 2. Define the native lab

```yaml
version: 1
project_root: ../permit-project

contract:
  path: contracts/Permit.py
  sender: cogent-direct
  check_pickling: true

cases:
  authoritative-source-contradicts-leader:
    method: assess
    args: ["https://evidence.example/licence"]
    expected_captures: 1
    validator_indices: all

    leader:
      web:
        - pattern: 'evidence\\.example/licence'
          status: 200
          body: '{"status":"active"}'

    validator:
      web:
        - pattern: 'evidence\\.example/licence'
          status: 200
          body: '{"status":"expired"}'
```

### 3. Validate the experiment definition

```bash
cogent validate \
  --fleet fleet.yaml \
  --corpus focused-corpus.yaml \
  --direct-lab direct-lab.yaml \
  --gltest
```

### 4. Execute the actual validator path

```bash
cogent run \
  --engine direct \
  --fleet fleet.yaml \
  --corpus focused-corpus.yaml \
  --direct-lab direct-lab.yaml \
  --repetitions 10 \
  --output observations.jsonl
```

Each observation records that it came from `genlayer-test-direct`, the contract/method, number of
captured nondeterministic blocks, validated indices, per-block validator booleans and leader timing.

Native mode is intentionally serial because Direct Mode uses process-global SDK/WASI/module state.
Cogent refuses unsafe parallelism instead of pretending it is isolated.

## Per-validator evidence profiles

A challenge can define a default validator environment and override specific fleet members:

```yaml
validator:
  web:
    - pattern: 'evidence\\.example/licence'
      status: 200
      body: '{"status":"active"}'

validators:
  validator-b:
    web:
      - pattern: 'evidence\\.example/licence'
        status: 200
        body: '{"status":"expired"}'
```

That lets a deterministic regression lab ask whether two validator paths respond the same way when
presented with different evidence conditions, while keeping the experiment fully reproducible.

## External runner mode

External runners remain useful when the experiment requires Studio, Studionet, testnet, live LLM
providers, browser-backed web behavior, or another project-specific harness.

```bash
cogent run \
  --engine external \
  --fleet examples/fleet.yaml \
  --corpus corpus/default.yaml \
  --runner 'python experiments/run_case.py' \
  --repetitions 3 \
  --workers 4 \
  --output observations.jsonl
```

Cogent supplies:

```text
COGENT_CHALLENGE_FILE
COGENT_VALIDATOR_FILE
COGENT_TRANSACTION_CONTEXT_FILE
COGENT_RUN_ID
COGENT_SEED
```

The external executable prints one final observation JSON line. See
[Runner Contract](docs/RUNNER_CONTRACT.md).

## GenLayer validator profile mapping

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

Cogent can round-trip these profiles through the installed official validator factory:

```bash
cogent validate --fleet fleet.yaml --corpus corpus.yaml --gltest
```

It can also export redacted `transaction_context` material:

```bash
cogent contexts --fleet fleet.yaml --output transaction-context.json
```

## Analysis

After either execution engine produces observations:

```bash
cogent analyze \
  --fleet fleet.yaml \
  --corpus corpus.yaml \
  --observations observations.jsonl \
  --committee-size 5 \
  --simulations 10000 \
  --output-dir cogent-report
```

Outputs:

```text
cogent-report/
  analysis.json
  report.md
```

### Validator failure rate

For challenges with an expected validator outcome, Cogent compares each observation with that expected
outcome. `ERROR`, `TIMEOUT` and `UNDETERMINED` count as failures for correctness metrics while
operational failures are also reported separately.

### Co-failure Jaccard

For validators A and B:

```text
|failures(A) ∩ failures(B)|
---------------------------
|failures(A) ∪ failures(B)|
```

This measures whether two validators fail on the same labeled cases.

### Failure phi

Cogent also computes phi correlation over binary fail/pass vectors. Clustering requires a configurable
minimum number of shared failures before a correlation edge is eligible.

### Effective empirical failure domains

After clustering, Cogent calculates inverse-Simpson concentration over stake share of the observed
failure clusters:

```text
1 / sum(cluster_stake_share^2)
```

The name is deliberate: this is an **effective empirical failure-domain count**, not a Nakamoto
coefficient and not proof that different clusters are independent.

### Committee simulation

Cogent performs deterministic-seed weighted sampling over the supplied fleet and replays observed
challenge behavior to estimate:

- same-cluster committee-majority rate;
- wrong-majority rate;
- correct-majority rate;
- undetermined rate.

The current simulator uses the fleet's supplied `stake` field as its sampling weight. This is an
empirical lab model, not yet a full reproduction of GenLayer's live stake/delegation selection formula.
That limitation is kept explicit rather than hidden.

## Drift

```bash
cogent drift \
  --corpus corpus.yaml \
  --baseline september.jsonl \
  --current october.jsonl \
  --output drift.json
```

For each validator Cogent reports shared events, outcome-change rate, baseline/current failure rates
and failure-rate delta.

## CI policy

```bash
cogent ci \
  --analysis cogent-report/analysis.json \
  --min-normalized-diversity 0.50 \
  --max-correlated-majority-rate 0.25 \
  --max-wrong-majority-rate 0.05
```

Validator-specific local policy:

```bash
cogent certify \
  --analysis cogent-report/analysis.json \
  --validator validator-a \
  --max-failure-rate 0.05 \
  --max-operational-failure-rate 0.02
```

"Certification" is a local policy decision over a declared empirical run. It is not an on-chain or
official GenLayer certification.

## Security and privacy

- Store provider environment-variable **names**, not literal API keys, in fleet profiles.
- Saved transaction-context exports redact secret/token/password-like fields.
- Cogent does not read an API key merely to render a report.
- External runners are arbitrary developer-supplied code and run with local process permissions.
- Native Direct Mode executes the developer's Intelligent Contract source in the local Direct Mode
  runtime; treat contract source as code.
- Error/log tails are bounded, but projects should not print secrets.

See [Security](docs/SECURITY.md).

## Repository purity

There is intentionally no `contracts/` directory in Cogent. Native integration tests generate temporary
contract fixtures during test execution rather than committing a Cogent-owned Intelligent Contract.
Cogent remains infrastructure for **other developers' GenLayer contracts and validators**.

## Commands

```text
cogent init             create starter fleet/corpus/external-runner/native-lab files
cogent validate         validate inputs, gltest profiles and native lab mappings
cogent contexts         export redacted gltest-compatible validator contexts
cogent runner-contract  print the external runner protocol
cogent run              execute external or native Direct Mode experiments
cogent analyze          generate metrics, clusters, simulation and reports
cogent simulate         print committee-risk metrics
cogent drift            compare two observation datasets
cogent certify          apply one validator readiness policy
cogent ci               enforce fleet-level CI thresholds
```

## Current evidence levels

Cogent deliberately distinguishes execution fidelity:

1. **Synthetic external smoke** — package/orchestration verification only.
2. **Native Direct Mode** — real user contract leader + captured GenLayer validator functions with
   reproducible mocks.
3. **Studio/Studionet/custom external runner** — full multi-validator network-style experiments when
   the project supplies that harness.
4. **Future network ingestion/replay** — planned live receipt/equivalence-output analysis.

No lower level is presented as if it were a higher one.

## GenLayer references

- Testing Intelligent Contracts: https://docs.genlayer.com/developers/intelligent-contracts/testing
- `genlayer-test` API: https://docs.genlayer.com/api-references/genlayer-test
- Studio validators: https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-studio/validators
- Validator setup / GenVM diagnostics: https://docs.genlayer.com/validators/setup-guide
- GenLayer testing suite: https://github.com/genlayerlabs/genlayer-testing-suite

## License

MIT. See [LICENSE](LICENSE).
