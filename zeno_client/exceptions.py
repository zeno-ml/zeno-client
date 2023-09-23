"""Exceptions for the Zeno Client."""


class APIError(Exception):
    """Exception raised when an API call fails."""

    def __init__(self, message, status_code):
        """Initialize exception."""
        super().__init__(message)
        self.status_code = status_code
