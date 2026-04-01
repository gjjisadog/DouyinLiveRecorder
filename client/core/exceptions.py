"""Core exceptions."""


class ClientError(Exception):
    """Base client exception."""


class PlatformNotSupportedError(ClientError):
    """Raised when no platform adapter matches the URL."""


class DependencyMissingError(ClientError):
    """Raised when runtime dependencies are unavailable."""
