from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .errors import ConfigError


class Outcome(StrEnum):
    """Validator-level behavioral outcome for one challenge execution."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    UNDETERMINED = "UNDETERMINED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"

    @classmethod
    def parse(cls, value: str | Outcome) -> Outcome:
        if isinstance(value, Outcome):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ConfigError(f"unknown outcome {value!r}; expected one of: {allowed}") from exc


@dataclass(frozen=True, slots=True)
class ValidatorProfile:
    id: str
    stake: float = 1.0
    provider: str = ""
    model: str = ""
    plugin: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    plugin_config: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidatorProfile:
        identifier = str(data.get("id", "")).strip()
        if not identifier:
            raise ConfigError("validator.id is required")
        try:
            stake = float(data.get("stake", 1.0))
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"validator {identifier!r} has invalid stake") from exc
        if stake <= 0:
            raise ConfigError(f"validator {identifier!r} stake must be > 0")
        return cls(
            id=identifier,
            stake=stake,
            provider=str(data.get("provider", "")),
            model=str(data.get("model", "")),
            plugin=str(data.get("plugin", "")),
            config=dict(data.get("config") or {}),
            plugin_config=dict(data.get("plugin_config") or {}),
            labels={str(k): str(v) for k, v in dict(data.get("labels") or {}).items()},
        )

    def to_dict(self, *, include_plugin_config: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "stake": self.stake,
            "provider": self.provider,
            "model": self.model,
            "plugin": self.plugin,
            "config": dict(self.config),
            "labels": dict(self.labels),
        }
        if include_plugin_config:
            result["plugin_config"] = dict(self.plugin_config)
        return result


@dataclass(frozen=True, slots=True)
class Challenge:
    id: str
    family: str
    description: str
    expected: Outcome | None = None
    tags: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Challenge:
        identifier = str(data.get("id", "")).strip()
        family = str(data.get("family", "")).strip()
        if not identifier:
            raise ConfigError("challenge.id is required")
        if not family:
            raise ConfigError(f"challenge {identifier!r} requires a family")
        expected_raw = data.get("expected")
        expected = None if expected_raw in (None, "", "UNKNOWN") else Outcome.parse(expected_raw)
        if expected not in (None, Outcome.ACCEPT, Outcome.REJECT):
            raise ConfigError(
                f"challenge {identifier!r} expected must be ACCEPT, REJECT, or omitted"
            )
        return cls(
            id=identifier,
            family=family,
            description=str(data.get("description", "")).strip(),
            expected=expected,
            tags=tuple(str(tag) for tag in (data.get("tags") or [])),
            payload=dict(data.get("payload") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family": self.family,
            "description": self.description,
            "expected": self.expected.value if self.expected else None,
            "tags": list(self.tags),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class Observation:
    validator_id: str
    challenge_id: str
    run_id: str
    outcome: Outcome
    latency_ms: float | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Observation:
        validator_id = str(data.get("validator_id", "")).strip()
        challenge_id = str(data.get("challenge_id", "")).strip()
        run_id = str(data.get("run_id", "0")).strip()
        if not validator_id or not challenge_id:
            raise ConfigError("observation requires validator_id and challenge_id")
        latency = data.get("latency_ms")
        try:
            latency_ms = None if latency is None else float(latency)
        except (TypeError, ValueError) as exc:
            raise ConfigError("observation latency_ms must be numeric") from exc
        return cls(
            validator_id=validator_id,
            challenge_id=challenge_id,
            run_id=run_id,
            outcome=Outcome.parse(data.get("outcome", "")),
            latency_ms=latency_ms,
            reason=str(data.get("reason", "")),
            metadata=dict(data.get("metadata") or {}),
        )

    @property
    def event_key(self) -> tuple[str, str]:
        return (self.challenge_id, self.run_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "challenge_id": self.challenge_id,
            "run_id": self.run_id,
            "outcome": self.outcome.value,
            "latency_ms": self.latency_ms,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
