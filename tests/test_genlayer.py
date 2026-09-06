from cogent.genlayer import (
    public_transaction_context,
    transaction_context,
    validator_to_genlayer_dict,
)
from cogent.models import ValidatorProfile


def test_validator_to_genlayer_shape_excludes_cogent_fields():
    profile = ValidatorProfile("v", 3, "p", "m", "plugin", {"temperature": 0.2}, {"api_key_env_var": "KEY"}, {"cluster": "x"})
    result = validator_to_genlayer_dict(profile)
    assert "id" not in result
    assert "labels" not in result
    assert result["stake"] == 3


def test_context_can_pin_genvm_datetime():
    profile = ValidatorProfile("v")
    result = transaction_context([profile], genvm_datetime="2026-01-01T00:00:00Z")
    assert result["genvm_datetime"] == "2026-01-01T00:00:00Z"


def test_public_context_redacts_literal_secret():
    profile = ValidatorProfile("v", plugin_config={"api_key": "literal-secret", "api_key_env_var": "SAFE_NAME"})
    result = public_transaction_context([profile])
    plugin_config = result["validators"][0]["plugin_config"]
    assert plugin_config["api_key"] == "<redacted>"
    assert plugin_config["api_key_env_var"] == "SAFE_NAME"
