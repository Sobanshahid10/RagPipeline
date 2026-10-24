"""Safe, actionable failures without provider payloads or credentials."""


class AnswerFailure(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
