from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Iterable, Type

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def retryable(
    exceptions: Iterable[Type[BaseException]] | Type[BaseException],
    attempts: int = 5,
    min_wait: float = 1,
    max_wait: float = 8,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator factory that retries the wrapped function on network/api failures.
    """

    if isinstance(exceptions, type):
        exception_condition = retry_if_exception_type(exceptions)
    else:
        exception_condition = retry_if_exception_type(tuple(exceptions))

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=min_wait, max=max_wait),
            retry=exception_condition,
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator
