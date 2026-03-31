"""Custom exceptions for the NetBrain API client."""


class NetBrainError(Exception):
    """Base exception for all NetBrain client errors."""


class NetBrainAuthError(NetBrainError):
    """Raised when authentication fails (login, token invalid, etc.)."""


class NetBrainAPIError(NetBrainError):
    """Raised when the NetBrain REST API returns an error response.

    Attributes:
        status_code: HTTP status code returned by the server.
        status_description: Human-readable error message from the API.
    """

    def __init__(self, message: str, status_code: int = 0, status_description: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.status_description = status_description


class NetBrainSessionError(NetBrainError):
    """Raised when an operation is attempted without an active session."""


class NetBrainNotFoundError(NetBrainAPIError):
    """Raised when the requested resource is not found (HTTP 404)."""
