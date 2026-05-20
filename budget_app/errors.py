from __future__ import annotations


class AppError(Exception):
    """User-facing application error with a recovery hint."""

    def __init__(self, message: str, hint: str = "", exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.exit_code = exit_code
