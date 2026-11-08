"""
Retry logic with exponential backoff for integration calls.
Uses tenacity with configurable retry counts and backoff.
"""
from __future__ import annotations
import asyncio
import random
from typing import Callable, Any
import structlog
import httpx

log = structlog.get_logger()


async def execute_with_retry(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    retryable_exceptions: tuple = (httpx.RequestError, httpx.HTTPStatusError, TimeoutError),
) -> Any:
    """Execute an async callable with exponential backoff and jitter."""
    attempt = 0
    while True:
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            # Only retry 5xx server errors, not 4xx client errors
            if 400 <= e.response.status_code < 500:
                raise
            attempt += 1
            if attempt > max_retries:
                log.error("Max retries exceeded for status error", status=e.response.status_code, attempts=attempt)
                raise
            delay = min(max_delay, initial_delay * (backoff_factor ** (attempt - 1)))
            jitter = random.uniform(0, 0.1 * delay)
            log.warning("Retrying failed HTTP call", attempt=attempt, delay=delay + jitter, error=str(e))
            await asyncio.sleep(delay + jitter)
        except retryable_exceptions as e:
            attempt += 1
            if attempt > max_retries:
                log.error("Max retries exceeded for request exception", attempts=attempt, error=str(e))
                raise
            delay = min(max_delay, initial_delay * (backoff_factor ** (attempt - 1)))
            jitter = random.uniform(0, 0.1 * delay)
            log.warning("Retrying failed network call", attempt=attempt, delay=delay + jitter, error=str(e))
            await asyncio.sleep(delay + jitter)
