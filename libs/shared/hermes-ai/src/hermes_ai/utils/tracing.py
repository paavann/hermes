from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Literal


def observe[**P, R](
    *,
    name: str,
    capture_input: bool = True,
    capture_output: bool = True,
    as_type: Literal["span"] = "span",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        wrapped: Callable[P, Awaitable[R]] | None = None

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal wrapped
            if wrapped is None:
                from langfuse import observe as langfuse_observe

                wrapped = langfuse_observe(
                    as_type=as_type,
                    name=name,
                    capture_input=capture_input,
                    capture_output=capture_output,
                )(func)
            return await wrapped(*args, **kwargs)

        return wrapper

    return decorator
