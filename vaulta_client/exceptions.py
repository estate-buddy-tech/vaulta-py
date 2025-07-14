"""
Custom exceptions for the Vaulta client.
"""

from typing import Optional, Dict, Any


class VaultaError(Exception):
    """Base exception for all Vaulta client errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class VaultaClientError(VaultaError):
    """Exception raised for client-side errors (4xx status codes)."""

    def __init__(
        self, message: str, status_code: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status_code, details)


class VaultaServerError(VaultaError):
    """Exception raised for server-side errors (5xx status codes)."""

    def __init__(
        self, message: str, status_code: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status_code, details)


class VaultaAuthenticationError(VaultaClientError):
    """Exception raised for authentication errors (401 status code)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, 401, details)


class VaultaNotFoundError(VaultaClientError):
    """Exception raised when a resource is not found (404 status code)."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, 404, details)


class VaultaValidationError(VaultaClientError):
    """Exception raised for validation errors (400 status code)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, details)
