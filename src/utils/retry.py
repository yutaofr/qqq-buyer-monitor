import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)

def exponential_backoff(
    retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retry_on: type[Exception] | tuple[type[Exception], ...] = Exception,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Universal exponential backoff decorator for network-bound tasks.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import random
            
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:
                    attempt += 1
                    if attempt > retries:
                        logger.error(
                            f"Final attempt failed for {func.__name__} after {retries} retries: {exc}"
                        )
                        raise
                    
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt}/{retries}) due to: {exc}"
                    )
                    time.sleep(delay)
        return wrapper
    return decorator
