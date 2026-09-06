# GenLayer integration

Cogent is an orchestration and analysis layer above existing GenLayer development tooling.

## Why it does not replace `genlayer-test`

The official testing suite already provides Direct Mode, Studio Mode, mocked web/LLM behavior,
custom validators, and `transaction_context`. Reimplementing those features would create a weaker
parallel simulator. Cogent instead uses the same validator vocabulary and lets the project runner use
the official execution path.

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

`cogent contexts` removes the Cogent-only `id` and `labels` fields and emits:

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

This mirrors the current `genlayer-test` non-mocked `Validator.to_dict()` structure. When the optional
`genlayer-test` dependency is installed, `cogent validate --gltest` round-trips every profile through
`get_validator_factory().create_validator(...).to_dict()` so upstream shape incompatibilities fail
early.

## Suggested real-runner pattern

A project's runner should:

1. read the Cogent challenge and validator context;
2. map the challenge payload to project-specific mocks/arguments;
3. use `get_contract_factory` and the transaction context in Studio Mode, or Direct Mode when the
   target behavior can be isolated there;
4. inspect the actual validator/consensus result relevant to the challenge;
5. emit one Cogent outcome JSON line.

Cogent deliberately does not prescribe one universal interpretation of `ACCEPT` because contracts can
use different equivalence principles and challenge semantics.

## Environment levels

Recommended progression:

1. synthetic runner — Cogent installation smoke test only;
2. Direct Mode — fast challenge mapping and deterministic mocks;
3. local Studio — custom heterogeneous validators and full consensus integration;
4. Studionet / testnet — smaller pre-production behavioral samples where appropriate.

Studio and live networks can differ in exact web behavior or chain-layer parity. Keep environment name
and transaction evidence in observation metadata when the distinction matters.
