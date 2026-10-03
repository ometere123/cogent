# Cogent strict 5x5 implementation record

## Baseline

- Starting commit: `7f3328758de6dbedabcb910c9780983d01c39182`.
- Working branch: `hardening/cogent-strict-5x5`.
- Canonical network target: Studionet, chain ID `61999` (`0xF22F`).
- Intended toolchain: Python 3.12, Python 3.13 compatibility CI, GenLayer CLI 0.39.1, `genlayer-test==0.29.2`, and stable `genlayer-js==1.1.8`.

## Baseline weaknesses discovered

1. Zero observed failures can be rendered as five singleton failure domains and normalized diversity `1.0`.
2. Semantic disagreement and execution/availability failures share one correlation channel.
3. Challenges lack expected-label oracle provenance and corpus identity.
4. Observations have no immutable experiment identity or tamper-evident artifact manifest.
5. Direct Mode can expose declared provider/model names although deterministic mocks executed the function.
6. Product logic currently uses the private `genlayer-test` validator capture shape.
7. No Cogent Intelligent Contract, immutable attestation lifecycle, adversarial challenge path, or frontend exists.
8. Dependency constraints are ranges rather than an auditable, pinned release envelope.

## Checkpoints

| Checkpoint | Scope | Status |
| --- | --- | --- |
| CP01 | Baseline audit and plan | complete: `a2329dc` |
| CP02 | Evidence sufficiency, fail-closed policy | complete: `4f2c192` |
| CP03 | Separate semantic, operational, availability, combined channels | complete: `0d8816a` |
| CP04 | Oracle provenance and experiment identity | pending |
| CP05 | Canonical artifacts and verifier | pending |
| CP06-07 | Attestation contract and adversarial tests | pending |
| CP08 | Studionet deployment evidence | blocked until verified CLI, wallet, and faucet access |
| CP09-11 | Next.js Explorer and wallet/finality workflow | pending |
| CP12 | Statistical, property, mutation hardening | pending |
| CP13-15 | Packaging, documentation, hostile audit | pending |

## Evidence record

Test counts, deployment receipts, and final commit are recorded here only after the corresponding command or chain readback succeeds. No live-chain or frontend deployment claim is made before that evidence exists.

### Local verification, 2026-10-03

- Python 3.12 test suite: `34 passed, 2 skipped`.
- The two skipped tests are native Direct Mode executions on Windows. `genlayer-test` currently leaves a temporary file locked and raises `PermissionError`; this is documented as an upstream Windows limitation rather than a pass.
- Studionet preset reports chain ID `61999`, which is the required canonical network.
- Deployment is blocked: installed GenLayer CLI is `0.40.0-rc.3`, not the required stable `0.39.1`. The hard gate prohibits substituting this release-candidate CLI for canonical evidence.
