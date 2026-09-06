from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError
from .models import Challenge, Observation, Outcome, ValidatorProfile


@dataclass(frozen=True, slots=True)
class DirectMocks:
    """Mocks applied to one GenLayer Direct Mode execution phase."""

    web: tuple[tuple[str, dict[str, Any]], ...] = ()
    llm: tuple[tuple[str, str], ...] = ()
    genvm_datetime: str | None = None


@dataclass(frozen=True, slots=True)
class DirectCase:
    """Contract method and leader/validator evidence for one Cogent challenge."""

    challenge_id: str
    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    leader: DirectMocks
    validator: DirectMocks
    validator_overrides: dict[str, DirectMocks]
    validator_indices: tuple[int, ...] | None
    expected_captures: int | None


@dataclass(frozen=True, slots=True)
class DirectLab:
    """Validated native Direct Mode experiment manifest."""

    source_path: Path
    project_root: Path
    contract_path: Path
    contract_ref: str
    constructor_args: tuple[Any, ...]
    constructor_kwargs: dict[str, Any]
    sdk_version: str | None
    sender_label: str
    check_pickling: bool
    cases: dict[str, DirectCase]


def _load_document(path: str | Path) -> tuple[Path, Any]:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise ConfigError(f"direct lab file not found: {source}")
    text = source.read_text(encoding="utf-8")
    try:
        if source.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot parse direct lab {source}: {exc}") from exc
    return source, data


def _expect_mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be a mapping")
    return dict(value)


def _expect_list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{label} must be a list")
    return list(value)


def _parse_web_mocks(value: Any, label: str) -> tuple[tuple[str, dict[str, Any]], ...]:
    records = _expect_list(value, label)
    parsed: list[tuple[str, dict[str, Any]]] = []
    for index, raw in enumerate(records):
        item = _expect_mapping(raw, f"{label}[{index}]")
        pattern = str(item.pop("pattern", "")).strip()
        if not pattern:
            raise ConfigError(f"{label}[{index}].pattern is required")
        explicit = item.pop("response", None)
        if explicit is not None:
            response = _expect_mapping(explicit, f"{label}[{index}].response")
            if item:
                unexpected = ", ".join(sorted(item))
                raise ConfigError(
                    f"{label}[{index}] cannot mix response with shorthand fields: {unexpected}"
                )
        else:
            response = item
        if not response:
            raise ConfigError(f"{label}[{index}] requires a web response")
        parsed.append((pattern, response))
    return tuple(parsed)


def _parse_llm_mocks(value: Any, label: str) -> tuple[tuple[str, str], ...]:
    records = _expect_list(value, label)
    parsed: list[tuple[str, str]] = []
    for index, raw in enumerate(records):
        item = _expect_mapping(raw, f"{label}[{index}]")
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            raise ConfigError(f"{label}[{index}].pattern is required")
        if "response" not in item:
            raise ConfigError(f"{label}[{index}].response is required")
        parsed.append((pattern, str(item["response"])))
    return tuple(parsed)


def _parse_mocks(
    value: Any,
    label: str,
    *,
    base: DirectMocks | None = None,
) -> DirectMocks:
    raw = _expect_mapping(value, label)
    inherited = base or DirectMocks()
    web = inherited.web
    llm = inherited.llm
    genvm_datetime = inherited.genvm_datetime
    if "web" in raw:
        web = _parse_web_mocks(raw.get("web"), f"{label}.web")
    if "llm" in raw:
        llm = _parse_llm_mocks(raw.get("llm"), f"{label}.llm")
    if "genvm_datetime" in raw:
        candidate = raw.get("genvm_datetime")
        genvm_datetime = None if candidate in (None, "") else str(candidate)
    unknown = sorted(set(raw) - {"web", "llm", "genvm_datetime"})
    if unknown:
        raise ConfigError(f"{label} has unknown fields: {', '.join(unknown)}")
    return DirectMocks(web=web, llm=llm, genvm_datetime=genvm_datetime)


def _parse_validator_indices(value: Any, label: str) -> tuple[int, ...] | None:
    if value in (None, "all"):
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return (value,)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{label} must be 'all', an integer, or a non-empty integer list")
    indices: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ConfigError(f"{label} must contain only integers")
        indices.append(item)
    return tuple(indices)


def load_direct_lab(
    path: str | Path,
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
) -> DirectLab:
    """Load and validate a declarative native GenLayer Direct Mode lab manifest."""

    source, raw_value = _load_document(path)
    raw = _expect_mapping(raw_value, "direct lab")
    if raw.get("version") != 1:
        raise ConfigError("direct lab version must be 1")

    root_value = str(raw.get("project_root", ".")).strip() or "."
    project_root = Path(root_value).expanduser()
    if not project_root.is_absolute():
        project_root = (source.parent / project_root).resolve()
    else:
        project_root = project_root.resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise ConfigError(f"direct lab project_root is not a directory: {project_root}")

    contract = _expect_mapping(raw.get("contract"), "direct lab.contract")
    contract_ref = str(contract.get("path", "")).strip()
    if not contract_ref:
        raise ConfigError("direct lab.contract.path is required")
    contract_path = Path(contract_ref).expanduser()
    if not contract_path.is_absolute():
        contract_path = (project_root / contract_path).resolve()
    else:
        contract_path = contract_path.resolve()
    if not contract_path.exists() or not contract_path.is_file():
        raise ConfigError(f"direct lab contract not found: {contract_path}")

    constructor_args = _expect_list(
        contract.get("constructor_args"), "direct lab.contract.constructor_args"
    )
    constructor_kwargs = _expect_mapping(
        contract.get("constructor_kwargs"), "direct lab.contract.constructor_kwargs"
    )
    sender_label = str(contract.get("sender", "cogent-direct")).strip() or "cogent-direct"
    sdk_value = contract.get("sdk_version")
    sdk_version = None if sdk_value in (None, "") else str(sdk_value)
    check_pickling = bool(contract.get("check_pickling", False))

    validator_ids = {item.id for item in validators}
    challenge_ids = {item.id for item in challenges}
    cases_raw = _expect_mapping(raw.get("cases"), "direct lab.cases")
    if not cases_raw:
        raise ConfigError("direct lab.cases must contain at least one challenge mapping")

    unknown_cases = sorted(set(cases_raw) - challenge_ids)
    if unknown_cases:
        raise ConfigError(
            "direct lab references challenge ids not present in the corpus: "
            + ", ".join(unknown_cases)
        )

    cases: dict[str, DirectCase] = {}
    for challenge_id, case_value in cases_raw.items():
        label = f"direct lab.cases.{challenge_id}"
        case = _expect_mapping(case_value, label)
        method = str(case.get("method", "")).strip()
        if not method:
            raise ConfigError(f"{label}.method is required")
        args = tuple(_expect_list(case.get("args"), f"{label}.args"))
        kwargs = _expect_mapping(case.get("kwargs"), f"{label}.kwargs")
        leader = _parse_mocks(case.get("leader"), f"{label}.leader")
        validator = _parse_mocks(case.get("validator"), f"{label}.validator")

        overrides_raw = _expect_mapping(case.get("validators"), f"{label}.validators")
        unknown_validators = sorted(set(overrides_raw) - validator_ids)
        if unknown_validators:
            raise ConfigError(
                f"{label}.validators references unknown fleet ids: "
                + ", ".join(unknown_validators)
            )
        overrides = {
            validator_id: _parse_mocks(
                override,
                f"{label}.validators.{validator_id}",
                base=validator,
            )
            for validator_id, override in overrides_raw.items()
        }

        expected_raw = case.get("expected_captures")
        if expected_raw is None:
            expected_captures = None
        else:
            if not isinstance(expected_raw, int) or isinstance(expected_raw, bool):
                raise ConfigError(f"{label}.expected_captures must be an integer")
            if expected_raw <= 0:
                raise ConfigError(f"{label}.expected_captures must be > 0")
            expected_captures = expected_raw

        indices = _parse_validator_indices(
            case.get("validator_indices", "all"), f"{label}.validator_indices"
        )
        cases[challenge_id] = DirectCase(
            challenge_id=challenge_id,
            method=method,
            args=args,
            kwargs=kwargs,
            leader=leader,
            validator=validator,
            validator_overrides=overrides,
            validator_indices=indices,
            expected_captures=expected_captures,
        )

    unknown_top = sorted(set(raw) - {"version", "project_root", "contract", "cases"})
    if unknown_top:
        raise ConfigError(f"direct lab has unknown fields: {', '.join(unknown_top)}")

    return DirectLab(
        source_path=source,
        project_root=project_root,
        contract_path=contract_path,
        contract_ref=contract_ref,
        constructor_args=tuple(constructor_args),
        constructor_kwargs=constructor_kwargs,
        sdk_version=sdk_version,
        sender_label=sender_label,
        check_pickling=check_pickling,
        cases=cases,
    )


def validate_direct_lab_coverage(lab: DirectLab, challenges: list[Challenge]) -> None:
    missing = [item.id for item in challenges if item.id not in lab.cases]
    if missing:
        raise ConfigError(
            "direct lab has no native case mapping for selected challenges: " + ", ".join(missing)
        )


def _import_gltest_direct() -> tuple[Any, Any, Any]:
    try:
        from gltest.direct import VMContext, create_address, deploy_contract
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "native Direct Mode requires genlayer-test; install Cogent with "
            "`pip install cogent-gl[genlayer]`"
        ) from exc
    return VMContext, create_address, deploy_contract


def _apply_mocks(vm: Any, mocks: DirectMocks) -> None:
    if mocks.genvm_datetime:
        vm.warp(mocks.genvm_datetime)
    for pattern, response in mocks.web:
        vm.mock_web(pattern, dict(response))
    for pattern, response in mocks.llm:
        vm.mock_llm(pattern, response)


def _capture_count(vm: Any) -> int:
    captured = getattr(vm, "_captured_validators", None)
    if not isinstance(captured, list):
        raise RuntimeError(
            "installed genlayer-test no longer exposes Direct Mode validator captures in the "
            "0.29.x-compatible shape"
        )
    return len(captured)


def _resolve_indices(case: DirectCase, capture_count: int) -> tuple[int, ...]:
    if case.validator_indices is None:
        return tuple(range(capture_count))
    resolved: list[int] = []
    for raw_index in case.validator_indices:
        index = raw_index if raw_index >= 0 else capture_count + raw_index
        if index < 0 or index >= capture_count:
            raise ConfigError(
                f"challenge {case.challenge_id!r} validator index {raw_index} is out of range "
                f"for {capture_count} captured nondeterministic blocks"
            )
        resolved.append(index)
    return tuple(dict.fromkeys(resolved))


def _error_observations(
    validators: list[ValidatorProfile],
    challenge: Challenge,
    repetition: int,
    *,
    reason: str,
    metadata: dict[str, Any],
    latency_ms: float | None = None,
) -> list[Observation]:
    return [
        Observation(
            validator_id=validator.id,
            challenge_id=challenge.id,
            run_id=str(repetition),
            outcome=Outcome.ERROR,
            latency_ms=latency_ms,
            reason=reason,
            metadata=dict(metadata),
        )
        for validator in validators
    ]


def _run_direct_case(
    validators: list[ValidatorProfile],
    challenge: Challenge,
    case: DirectCase,
    lab: DirectLab,
    repetition: int,
) -> list[Observation]:
    VMContext, create_address, deploy_contract = _import_gltest_direct()
    vm = VMContext()
    vm.sender = create_address(lab.sender_label)
    vm.check_pickling = lab.check_pickling
    common_metadata: dict[str, Any] = {
        "engine": "genlayer-test-direct",
        "contract": lab.contract_ref,
        "method": case.method,
        "repetition": repetition,
    }

    leader_started = time.perf_counter()
    try:
        with vm.activate():
            _apply_mocks(vm, case.leader)
            contract = deploy_contract(
                lab.contract_path,
                vm,
                *lab.constructor_args,
                sdk_version=lab.sdk_version,
                **lab.constructor_kwargs,
            )
            vm.clear_validators()
            method = getattr(contract, case.method, None)
            if method is None or not callable(method):
                raise ConfigError(
                    f"contract {lab.contract_ref!r} has no callable method {case.method!r}"
                )
            method(*case.args, **case.kwargs)
            leader_latency_ms = (time.perf_counter() - leader_started) * 1000
            capture_count = _capture_count(vm)
            common_metadata["leader_latency_ms"] = round(leader_latency_ms, 3)
            common_metadata["captured_nondet_blocks"] = capture_count

            if capture_count == 0:
                return _error_observations(
                    validators,
                    challenge,
                    repetition,
                    reason=(
                        "native Direct Mode leader execution captured no gl.vm.run_nondet "
                        "validator functions"
                    ),
                    metadata=common_metadata,
                    latency_ms=leader_latency_ms,
                )
            if case.expected_captures is not None and capture_count != case.expected_captures:
                return _error_observations(
                    validators,
                    challenge,
                    repetition,
                    reason=(
                        f"expected {case.expected_captures} captured nondeterministic blocks, "
                        f"observed {capture_count}"
                    ),
                    metadata=common_metadata,
                    latency_ms=leader_latency_ms,
                )

            indices = _resolve_indices(case, capture_count)
            common_metadata["validated_indices"] = list(indices)
            post_leader_snapshot = vm.snapshot()
            observations: list[Observation] = []

            for validator in validators:
                vm.revert(post_leader_snapshot)
                vm.clear_mocks()
                validator_mocks = case.validator_overrides.get(validator.id, case.validator)
                _apply_mocks(vm, validator_mocks)
                started = time.perf_counter()
                try:
                    block_results = [bool(vm.run_validator(index=index)) for index in indices]
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    agreed = all(block_results)
                    failed_indices = [
                        index for index, result in zip(indices, block_results, strict=True) if not result
                    ]
                    metadata = {
                        **common_metadata,
                        "validator_results": block_results,
                        "validator_profile": validator.id,
                    }
                    if agreed:
                        reason = (
                            f"validator agreed with all {len(block_results)} selected "
                            "nondeterministic blocks"
                        )
                        outcome = Outcome.ACCEPT
                    else:
                        reason = "validator disagreed with nondeterministic blocks: " + ", ".join(
                            str(index) for index in failed_indices
                        )
                        outcome = Outcome.REJECT
                    observations.append(
                        Observation(
                            validator_id=validator.id,
                            challenge_id=challenge.id,
                            run_id=str(repetition),
                            outcome=outcome,
                            latency_ms=elapsed_ms,
                            reason=reason,
                            metadata=metadata,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - validator failure is experimental evidence
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    observations.append(
                        Observation(
                            validator_id=validator.id,
                            challenge_id=challenge.id,
                            run_id=str(repetition),
                            outcome=Outcome.ERROR,
                            latency_ms=elapsed_ms,
                            reason=f"validator execution raised {type(exc).__name__}: {exc}",
                            metadata={
                                **common_metadata,
                                "validator_profile": validator.id,
                                "error_type": type(exc).__name__,
                            },
                        )
                    )
            return observations
    except Exception as exc:  # noqa: BLE001 - leader/deploy errors become observations
        elapsed_ms = (time.perf_counter() - leader_started) * 1000
        return _error_observations(
            validators,
            challenge,
            repetition,
            reason=f"native Direct Mode leader execution raised {type(exc).__name__}: {exc}",
            metadata={**common_metadata, "error_type": type(exc).__name__},
            latency_ms=elapsed_ms,
        )


def run_direct_matrix(
    validators: list[ValidatorProfile],
    challenges: list[Challenge],
    lab_path: str | Path,
    *,
    repetitions: int = 1,
) -> list[Observation]:
    """Execute a Cogent matrix through real genlayer-test Direct Mode validator functions."""

    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    lab = load_direct_lab(lab_path, validators, challenges)
    validate_direct_lab_coverage(lab, challenges)

    observations: list[Observation] = []
    for challenge in challenges:
        case = lab.cases[challenge.id]
        for repetition in range(repetitions):
            observations.extend(
                _run_direct_case(validators, challenge, case, lab, repetition)
            )
    observations.sort(key=lambda item: (item.challenge_id, item.validator_id, item.run_id))
    return observations
