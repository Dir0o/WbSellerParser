import time
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")

def log_elapsed(label: str | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Декоратор: выводит время выполнения функции.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            name = label or func.__name__
            print(f"{name}: {elapsed:.1f} ms")
            return result
        return wrapper
    return decorator