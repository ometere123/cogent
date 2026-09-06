from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from .errors import ConfigError
from .models import Challenge, Observation, ValidatorProfile


def _load_structured(path: str | Path) -> Any:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(text)
        return json.loads(text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot parse {path}: {exc}") from exc


def load_fleet(path: str | Path) -> list[ValidatorProfile]:
    raw = _load_structured(path)
    if not isinstance(raw, dict) or not isinstance(raw.get("validators"), list):
        raise ConfigError("fleet file must contain a top-level validators list")
    validators = [ValidatorProfile.from_dict(item) for item in raw["validators"]]
    ids = [item.id for item in validators]
    if len(ids) != len(set(ids)):
        raise ConfigError("validator ids must be unique")
    if not validators:
        raise ConfigError("fleet must contain at least one validator")
    return validators


def load_corpus(path: str | Path) -> list[Challenge]:
    raw = _load_structured(path)
    if not isinstance(raw, dict) or not isinstance(raw.get("challenges"), list):
        raise ConfigError("corpus file must contain a top-level challenges list")
    challenges = [Challenge.from_dict(item) for item in raw["challenges"]]
    ids = [item.id for item in challenges]
    if len(ids) != len(set(ids)):
        raise ConfigError("challenge ids must be unique")
    if not challenges:
        raise ConfigError("corpus must contain at least one challenge")
    return challenges


def load_observations(path: str | Path) -> list[Observation]:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"file not found: {path}")
    observations: list[Observation] = []
    if path.suffix.lower() == ".jsonl":
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ConfigError(f"invalid JSONL at {path}:{lineno}: {exc}") from exc
            observations.append(Observation.from_dict(data))
    else:
        raw = _load_structured(path)
        records = raw.get("observations") if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ConfigError("observation file must be JSONL or a JSON/YAML list")
        observations = [Observation.from_dict(item) for item in records]
    if not observations:
        raise ConfigError("observation dataset is empty")
    return observations


def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
