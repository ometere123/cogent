from __future__ import annotations

from typing import Any

SENSITIVE_FRAGMENTS = ("secret", "token", "password", "private_key", "apikey", "api_key")


def redact(value: Any) -> Any:
    """Recursively redact secret-looking keys before writing reports or artifacts."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(fragment in normalized for fragment in SENSITIVE_FRAGMENTS):
                # Environment-variable *names* are safe and useful for reproducibility.
                if normalized.endswith("env_var") or normalized.endswith("env"):
                    result[key] = item
                else:
                    result[key] = "<redacted>"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value
