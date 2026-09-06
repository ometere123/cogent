class CogentError(Exception):
    """Base error for user-facing Cogent failures."""


class ConfigError(CogentError):
    """Raised when fleet, corpus, or observation data is invalid."""


class RunnerError(CogentError):
    """Raised when an external experiment runner cannot be executed."""
