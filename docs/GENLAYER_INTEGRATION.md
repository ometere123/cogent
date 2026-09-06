# GenLayer integration

Cogent is an orchestration and analysis layer for GenLayer validator behavior. v0.2 has two execution
boundaries, and the evidence level is always recorded explicitly.

## Native Direct Mode

Native mode uses the official `gltest.direct` surface from `genlayer-test` rather than implementing a
parallel VM:

```python
from gltest.direct import VMContext, create_address, deploy_contract
```

Cogent deploys the developer's Intelligent Contract in Direct Mode, applies leader mocks, calls the
configured contract method, verifies that one or more `gl.vm.run_nondet` validator functions were
captured, swaps to validator evidence/mocks, and invokes:

```python
vm.run_validator(index=...)
```

The resulting boolean becomes the per-validator Cogent observation. This directly exercises the
contract's captured GenLayer validator function; Cogent does not synthesize or predict the vote.

See `docs/NATIVE_DIRECT_MODE.md` for the manifest and fidelity boundary.

## External runner mode

External runners remain supported because some experiments require surfaces Direct Mode does not
provide: Studio/Studionet transactions, live providers, browser-backed web behavior, custom local
infrastructure, transaction receipts or future network replay.

The external mode contract is documented in `docs/RUNNER_CONTRACT.md`.

## Why Cogent does not replace `genlayer-test`

The official testing suite already provides Direct Mode, Studio Mode, mocked web/LLM behavior, custom
validators, transaction contexts and simulator support. Reimplementing those features would create a
weaker parallel stack.

Cogent adds a different layer:

- challenge-corpus orchestration;
- per-validator behavioral observations;
- co-failure and correlation analysis;
- empirical failure-domain clustering;
- committee-risk simulation;
- drift and CI/readiness policy.

Where GenLayer execution is needed, Cogent delegates execution semantics to the official tooling.

## Validator profile mapping

A Cogent profile contains:

```yaml
id: validator-a
stake: 10
provider: openai
model: gpt-4o
config: {temperature: 0.2}
plugin: openai-compatible
plugin_config: {api_key_env_var: OPENAI_API_KEY}
```

`cogent contexts` removes Cogent-only `id` and `labels` fields and emits:

```json
{
  "validators": [{
    "stake": 10,
    "provider": "openai",
    "model": "gpt-4o",
    "config": {"temperature": 0.2},
    "plugin": "openai-compatible",
    "plugin_config": {"api_key_env_var": "OPENAI_API_KEY"}
  }]
}
```

When `genlayer-test` is installed, `cogent validate --gltest` round-trips every profile through
`get_validator_factory().create_validator(...).to_dict()`. Upstream shape incompatibilities therefore
fail before an experiment starts.

## Execution evidence levels

Cogent deliberately distinguishes these levels:

1. **Synthetic external smoke** — verifies package/orchestration/reporting only.
2. **Native Direct Mode** — executes real user-contract leader and captured validator functions through
   official `genlayer-test` Direct Mode with reproducible mocks.
3. **Studio/Studionet/testnet external runner** — project-specific multi-validator/network-style
   experiments using the official Studio tooling.
4. **Future live receipt/replay integration** — planned transaction/committee/equivalence-output
   ingestion.

The tool never describes a lower level as if it were a higher one.

## Native Direct Mode caveat on fleet model fields

Direct Mode with deterministic mocks measures the **contract validator path under declared evidence
conditions**. It does not itself invoke the `provider`/`model` named in a fleet profile. Those fields
become operational only when an engine actually uses the corresponding live provider, for example a
Studio/testnet external runner.

This distinction prevents a deterministic regression test from being misrepresented as a benchmark of
a production LLM.

## Suggested progression for a real project

1. Build focused native Direct Mode cases for known equivalence/evidence failure modes.
2. Make those cases permanent CI regressions.
3. Run the same conceptual corpus against heterogeneous Studio validators where live-provider behavior
   matters.
4. Preserve environment/network/transaction evidence in observation metadata.
5. Compare runs with `cogent drift` after contract, provider or model changes.

Studio and live networks can differ from Direct Mode in web behavior, sandbox/runtime fidelity,
committee/finality behavior and appeals. Those differences are evidence, not something Cogent hides.
