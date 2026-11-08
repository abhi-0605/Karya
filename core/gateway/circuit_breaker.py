"""
Circuit Breaker implementation for external integration adapters.
States: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
"""
from __future__ import annotations
import time
from enum import Enum
from typing import Optional
import structlog

log = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenException(Exception):
    """Raised when calls are attempted on an open circuit."""
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout_s: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout_s = reset_timeout_s
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.monotonic()

    def allow_request(self) -> bool:
        """Check whether a request is permitted to proceed."""
        now = time.monotonic()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if reset timeout has elapsed
            if now - self.last_failure_time >= self.reset_timeout_s:
                log.info("Circuit breaker transitioning OPEN -> HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # In half-open, allow one probe call
            return True

        return False

    def record_success(self) -> None:
        """Record successful call; resets counter and closes circuit."""
        if self.state != CircuitState.CLOSED:
            log.info("Circuit breaker closed after recovery")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def record_failure(self) -> None:
        """Record failed call; increments counter and trips circuit if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            log.warning(
                "Circuit breaker tripped to OPEN",
                failures=self.failure_count,
                threshold=self.failure_threshold,
            )
            self.state = CircuitState.OPEN
            self.last_state_change = self.last_failure_time
