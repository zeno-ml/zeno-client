"""Exceptions for the Zeno Client."""


class APIError(Exception):
    """Exception raised when an API call fails."""

    def __init__(self, message: str, status_code: int):
        """Initialize exception.

        Args:
            message (str): the error message.
            status_code (int): the HTTP status code.
        """
        super().__init__(message)
        self.status_code = status_code


class ClientVersionError(Exception):
    """Exception raised when the client version is incompatible with the backend."""

    def __init__(self, message: str):
        """Initialize exception.

        Args:
            message (str): the error message.
        """
        super().__init__(message)
