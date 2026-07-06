class DestinationError(Exception):
    pass


class DestinationConfigError(DestinationError):
    """Raised at startup if a destination YAML config is malformed or misnamed."""


class DestinationRegistryError(DestinationError):
    """Raised when destination configs cannot be loaded at startup."""
