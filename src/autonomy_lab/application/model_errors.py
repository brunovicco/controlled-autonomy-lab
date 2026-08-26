"""Provider-neutral errors raised across model adapters."""


class ModelProviderError(RuntimeError):
    """Raised when an external model provider cannot return a valid turn."""


class ModelRateLimitError(ModelProviderError):
    """Raised when a provider rejects a request because of rate limiting."""

    def __init__(self, message: str, *, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
