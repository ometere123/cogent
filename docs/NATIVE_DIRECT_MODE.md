# Native GenLayer Direct Mode

Cogent v0.2 can execute GenLayer validator functions itself. This closes the largest gap in the
original v0.1 architecture, where Cogent orchestrated experiments but an external process was
responsible for turning project-specific execution into `ACCEPT` or `REJECT` observations.

The external runner remains available for custom Studio/testnet/live-provider setups. Native Direct
Mode is the preferred reproducible contract-level laboratory when a challenge can be expressed with
GenLayer Direct Mode web/LLM mocks.

## What is actually executed

Native mode imports the public `gltest.direct` API from the official `genlayer-test` package:

- `VMContext`
- `create_address`
- `deploy_contract`
- `VMContext.run_validator()`

For one challenge, Cogent performs:

```text
user's Intelligent Contract source
             |
      deploy_contract(...)
             |
       leader mocks
             |
     contract method call
             |
      gl.vm.run_nondet
             |
 GenLayer Direct Mode captures
 (leader_result, leader_fn, validator_fn)
             |
      validator mocks
             |
 vm.run_validator(index=...)
             |
      True / False
             |
 Cogent ACCEPT / REJECT observation
```

`run_validator()` is not reimplemented by Cogent. It is the validator-execution mechanism supplied by
`genlayer-test`: after the leader path captures a nondeterministic block, the captured validator
function is run against the leader result. Swapping mocks between the leader call and validator call
allows the validator to observe different external evidence.

## Why this is different from the external runner

v0.1 external mode:

```text
Cogent -> arbitrary command -> command prints {"outcome":"REJECT"}
```

Cogent can validate the process boundary and preserve the observation, but it cannot prove that the
external program actually executed a GenLayer validator function.

v0.2 native mode:

```text
Cogent -> genlayer-test Direct VM -> user's leader_fn -> user's validator_fn -> bool
```

The observation therefore comes directly from the Intelligent Contract's captured GenLayer validator
logic. There is no user-controlled outcome JSON between the validator and Cogent.

## Installation

```bash
pip install -e '.[genlayer]'
```

The `genlayer-test` Direct runner resolves the GenVM/SDK runner bundle from the contract dependency
header (or an explicitly supplied `sdk_version`). Cogent intentionally delegates SDK loading and
calldata behavior to upstream `genlayer-test` rather than maintaining a second GenVM compatibility
layer.

## Lab manifest

A native run needs a lab manifest. The manifest is project-specific because Cogent cannot infer how a
generic challenge such as source conflict maps into a contract's method, arguments and nondeterministic
evidence.

```yaml
version: 1
project_root: ../my-genlayer-project

contract:
  path: contracts/Permit.py
  sender: cogent-direct
  constructor_args: []
  constructor_kwargs: {}
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

The manifest is validated by Cogent and has a published JSON Schema at
`schemas/direct-lab.schema.json`.

### Contract fields

- `path`: path to the developer's Intelligent Contract. Required.
- `sender`: deterministic Direct Mode sender seed.
- `constructor_args` / `constructor_kwargs`: arguments passed through the upstream Direct Mode deploy
  path, including its calldata round-trip checks.
- `sdk_version`: optional explicit GenVM release pin. When omitted, upstream Direct Mode resolution is
  used.
- `check_pickling`: asks Direct Mode to warn when nondeterministic closures would not serialize in
  production.

### Case fields

- `method`: public contract method that captures one or more `gl.vm.run_nondet` validator functions.
- `args` / `kwargs`: method inputs.
- `leader`: web/LLM mocks and optional GenVM datetime used during leader execution.
- `validator`: default mocks used when each validator executes the captured validator path.
- `validators`: optional per-fleet-validator mock overrides.
- `validator_indices`: which captured nondeterministic blocks to validate; `all` is the default.
- `expected_captures`: optional assertion on the number of captured nondeterministic blocks.

A lab must map every challenge in the corpus supplied to that native run. Use focused corpus files for
focused experiments instead of silently skipping unmapped challenges.

## Per-validator evidence

Cogent's fleet still names the validators whose behavior is being measured. A case can provide a
default validator evidence environment, then override specific validators:

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

This produces separate observations from the same captured leader result. It is useful for deterministic
correlated-failure regression suites: every validator sees the exact evidence profile declared for it.

Direct Mode mocks do **not** claim to measure a named production LLM model. Provider/model fields in a
Cogent fleet remain descriptive unless the chosen execution engine actually invokes those providers.
Studio/testnet/live-provider execution is a separate evidence level.

## Run

```bash
cogent validate \
  --fleet fleet.yaml \
  --corpus focused-corpus.yaml \
  --direct-lab direct-lab.yaml

cogent run \
  --engine direct \
  --fleet fleet.yaml \
  --corpus focused-corpus.yaml \
  --direct-lab direct-lab.yaml \
  --repetitions 10 \
  --output observations.jsonl
```

Native mode intentionally runs serially. Direct Mode mutates process-global SDK/WASI/module state while
loading Intelligent Contracts, so Cogent refuses `--workers` values other than `1` rather than adding
unsafe parallelism.

## Observation evidence

Native observations include metadata such as:

```json
{
  "engine": "genlayer-test-direct",
  "contract": "contracts/Permit.py",
  "method": "assess",
  "captured_nondet_blocks": 1,
  "validated_indices": [0],
  "validator_results": [false],
  "validator_profile": "validator-b",
  "leader_latency_ms": 18.23
}
```

The primary outcome mapping is deliberately simple:

- every selected captured validator function returned `True` -> `ACCEPT`
- at least one returned `False` -> `REJECT`
- validator exception -> `ERROR`
- deployment/leader/capture error -> `ERROR` for every validator in that challenge run

This is validator-level behavioral evidence, not a claim that Cogent has reproduced the full GenLayer
network transaction lifecycle.

## Fidelity boundary

Native Direct Mode is strong contract-level evidence, but it is not Studio or a live GenLayer network.
It does not prove:

- actual committee selection;
- network finality or appeals;
- production GenVM sandbox parity for every feature;
- live provider behavior when mocks are used;
- production web timing/network conditions.

Those limitations are intentional and should be stated in submission/research evidence. The next
integration tier is Studio/Studionet transaction ingestion and replay, not pretending Direct Mode is a
full network.
