from __future__ import annotations

from typing import Any

from .models import ValidatorProfile
from .redaction import redact


def validator_to_genlayer_dict(profile: ValidatorProfile) -> dict[str, Any]:
    """Translate a Cogent validator profile to the structure accepted by gltest contexts.

    The shape mirrors genlayer-test's Validator.to_dict() for non-mocked validators.
    Cogent deliberately stores environment-variable names, not the referenced secret values.
    """
    return {
        "stake": profile.stake,
        "provider": profile.provider,
        "model": profile.model,
        "config": dict(profile.config),
        "plugin": profile.plugin,
        "plugin_config": dict(profile.plugin_config),
    }


def transaction_context(
    validators: list[ValidatorProfile], *, genvm_datetime: str | None = None
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "validators": [validator_to_genlayer_dict(item) for item in validators]
    }
    if genvm_datetime:
        context["genvm_datetime"] = genvm_datetime
    return context


def public_transaction_context(
    validators: list[ValidatorProfile], *, genvm_datetime: str | None = None
) -> dict[str, Any]:
    """Redacted context suitable for saved artifacts and reports."""
    return redact(transaction_context(validators, genvm_datetime=genvm_datetime))


def validate_with_gltest(profile: ValidatorProfile) -> dict[str, Any]:
    """Round-trip a profile through genlayer-test when the optional dependency is installed."""
    try:
        from gltest import get_validator_factory
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "genlayer-test is not installed; install Cogent with `pip install cogent-gl[genlayer]`"
        ) from exc

    factory = get_validator_factory()
    validator = factory.create_validator(
        stake=int(profile.stake),
        provider=profile.provider,
        model=profile.model,
        config=profile.config,
        plugin=profile.plugin,
        plugin_config=profile.plugin_config,
    )
    return validator.to_dict()
