class SourceError(Exception):
    pass


class SourceConfigError(SourceError):
    """Raised at startup if a source's YAML config is malformed or misnamed."""


class SourceAuthError(SourceError):
    """Raised on 401 from a source API so callers can refresh the access token."""


class SourceRegistryError(SourceError):
    """Raised when source configs and connectors cannot be wired at startup."""


class SourceNotConnectedError(SourceError):
    pass


class SourceRateLimitError(SourceError):
    pass


class ModuleUnavailableError(SourceError):
    pass
