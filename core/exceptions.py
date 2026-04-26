"""Custom exceptions for the Nobitex quant system.

Limitations:
- Exceptions are lightweight and do not include structured remediation metadata.
"""


class NobitexError(Exception):
    """Base exception for the application."""


class APIRequestError(NobitexError):
    """Raised when a Nobitex API request fails."""


class RateLimitError(NobitexError):
    """Raised when the configured rate limit is exceeded."""


class ValidationError(NobitexError):
    """Raised when an input or strategy fails validation."""
