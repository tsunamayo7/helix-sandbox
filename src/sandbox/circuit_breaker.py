"""Helix AI Studio — Circuit Breaker for Sandbox Connections

Circuit Breaker pattern implementation to handle sandbox connection failures gracefully.
When failures exceed threshold, the circuit opens and rejects requests temporarily,
allowing the system to recover.

v13.0: Initial implementation
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests allowed
    OPEN = "open"           # Failure detected, requests blocked
    HALF_OPEN = "half_open" # Testing recovery, limited requests allowed


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""
    pass


@dataclass
class CircuitBreaker:
    """Circuit Breaker for protecting sandbox connections.

    Usage:
        breaker = CircuitBreaker()

        # Option 1: Decorator style
        @breaker.protect
        def connect_to_sandbox():
            # ... connection logic
            pass

        # Option 2: Context manager style
        with breaker:
            result = connect_to_sandbox()

        # Option 3: Direct call
        result = breaker.call(connect_to_sandbox)
    """
    # Configuration
    failure_threshold: int = 3          # Consecutive failures to trip the circuit
    recovery_timeout: float = 30.0      # Seconds to wait before trying again
    success_threshold: int = 2          # Successes needed to close circuit from half-open
    name: str = "sandbox"               # Identifier for logging

    # State (use field with default_factory for mutable defaults)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _last_state_change: float = field(default_factory=time.time, init=False)

    def __post_init__(self):
        """Initialize logger after dataclass init."""
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state with logging."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._last_state_change = time.time()
            self._logger.info(
                f"Circuit '{self.name}' state change: {old_state.value} -> {new_state.value}"
            )

    def _on_success(self):
        """Handle successful operation."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self._logger.debug(
                f"Circuit '{self.name}' half-open success {self._success_count}/{self.success_threshold}"
            )
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def _on_failure(self, error: Exception):
        """Handle failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._logger.warning(
            f"Circuit '{self.name}' failure {self._failure_count}/{self.failure_threshold}: {error}"
        )

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens the circuit
            self._transition_to(CircuitState.OPEN)
            self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from func (after recording failure)
        """
        # Check state (this also handles timeout transition)
        current_state = self.state

        if current_state == CircuitState.OPEN:
            remaining = self.recovery_timeout - (time.time() - self._last_failure_time)
            raise CircuitOpenError(
                f"Circuit '{self.name}' is open. "
                f"Retry in {remaining:.1f} seconds."
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def __enter__(self):
        """Context manager entry - check if requests are allowed."""
        current_state = self.state
        if current_state == CircuitState.OPEN:
            remaining = self.recovery_timeout - (time.time() - self._last_failure_time)
            raise CircuitOpenError(
                f"Circuit '{self.name}' is open. "
                f"Retry in {remaining:.1f} seconds."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record success or failure."""
        if exc_type is None:
            self._on_success()
        else:
            if exc_val is not None:
                self._on_failure(exc_val)
        return False  # Don't suppress exceptions

    def protect(self, func: Callable) -> Callable:
        """Decorator to protect a function with this circuit breaker.

        Example:
            breaker = CircuitBreaker()

            @breaker.protect
            def risky_operation():
                # ... code that might fail
                pass
        """
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        self._transition_to(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._logger.info(f"Circuit '{self.name}' manually reset")

    def get_status(self) -> dict:
        """Get current circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "success_threshold": self.success_threshold,
            }
        }


# Global circuit breakers for different sandbox backends
docker_circuit = CircuitBreaker(name="docker", failure_threshold=3, recovery_timeout=30.0)
windows_sandbox_circuit = CircuitBreaker(name="windows_sandbox", failure_threshold=2, recovery_timeout=60.0)
