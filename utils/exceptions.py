"""
Common exceptions for TradeLink API.
"""


class TradeLinkException(Exception):
    """Base exception for TradeLink application."""
    pass


class ValidationError(TradeLinkException):
    """Raised when validation fails."""
    pass


class AuthenticationError(TradeLinkException):
    """Raised when authentication fails."""
    pass


class PermissionError(TradeLinkException):
    """Raised when user doesn't have required permission."""
    pass


class NotFoundError(TradeLinkException):
    """Raised when requested resource is not found."""
    pass


class ConflictError(TradeLinkException):
    """Raised when there's a conflict (e.g., duplicate entry)."""
    pass
