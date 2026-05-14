"""
retry_handler.py - Retry decorator with exponential backoff for transient failures.

From the hackathon PDF Section 7.2:
  Provides @with_retry decorator that intercepts TransientError exceptions
  and retries with exponential backoff up to max_delay seconds.
"""

import time
import logging
from functools import wraps
from typing import Callable, Type

logger = logging.getLogger(__name__)


class TransientError(Exception):
    """
    Exception raised for transient failures that are safe to retry.
    Examples: network timeout, API rate limit, temporary service unavailability.
    """
    pass


class PermanentError(Exception):
    """
    Exception raised for failures that should NOT be retried.
    Examples: authentication failure, invalid request, insufficient permissions.
    """
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: tuple = (TransientError,),
    log_prefix: str = ""
):
    """
    Decorator that retries a function on transient failures with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 1)
        max_delay: Maximum delay between retries in seconds (default: 60)
        retry_exceptions: Tuple of exception types to retry on
        log_prefix: Optional prefix for log messages

    Usage:
        @with_retry(max_attempts=5, base_delay=2)
        def call_gmail_api():
            response = gmail_service.users().messages().list(userId='me').execute()
            if response.get('error'):
                raise TransientError("API temporary failure")
            return response

        # Or with custom exceptions:
        @with_retry(retry_exceptions=(TransientError, ConnectionError))
        def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        prefix = f"{log_prefix} " if log_prefix else ""
                        logger.warning(
                            f"{prefix}Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{prefix}All {max_attempts} attempts failed. Last error: {e}"
                        )
                except PermanentError:
                    logger.error(f"{log_prefix} Permanent error, not retrying: {last_exception}")
                    raise
            raise TransientError(
                f"{log_prefix}Failed after {max_attempts} attempts. Last error: {last_exception}"
            )
        return wrapper
    return decorator


def retry_on_transient(func: Callable) -> Callable:
    """
    Simplified decorator using default retry settings.

    Usage:
        @retry_on_transient
        def fetch_email_list():
            ...
    """
    return with_retry()(func)


# Example usage and self-test
if __name__ == "__main__":
    import random

    attempt_counter = 0

    @with_retry(max_attempts=3, base_delay=0.1, max_delay=1.0, log_prefix="[TEST]")
    def flaky_function():
        """Simulates a function that fails twice then succeeds."""
        global attempt_counter
        attempt_counter += 1
        if attempt_counter < 3:
            raise TransientError("Simulated network timeout")
        return {"status": "success", "data": "result"}

    # Test 1: Should succeed after retries
    attempt_counter = 0
    result = flaky_function()
    assert result["status"] == "success"
    assert attempt_counter == 3
    print(f"✓ Test 1 passed: succeeded after {attempt_counter} attempts")

    # Test 2: Should fail after max attempts
    attempt_counter = 0

    @with_retry(max_attempts=2, base_delay=0.1, max_delay=0.5, log_prefix="[TEST2]")
    def always_failing():
        raise TransientError("Always fails")

    try:
        always_failing()
        assert False, "Should have raised TransientError"
    except TransientError as e:
        print(f"✓ Test 2 passed: raised TransientError after max attempts: {e}")

    # Test 3: PermanentError should not be retried
    @with_retry(max_attempts=5, base_delay=0.1, log_prefix="[TEST3]")
    def permanent_failure():
        raise PermanentError("Authentication failed")

    try:
        permanent_failure()
        assert False, "Should have raised PermanentError"
    except PermanentError:
        print("✓ Test 3 passed: PermanentError not retried")

    # Test 4: Custom retry exceptions
    @with_retry(
        max_attempts=3,
        base_delay=0.1,
        retry_exceptions=(TransientError, ConnectionError),
        log_prefix="[TEST4]"
    )
    def connection_error_func():
        raise ConnectionError("Connection refused")

    try:
        connection_error_func()
        assert False, "Should have raised"
    except TransientError:
        print("✓ Test 4 passed: ConnectionError caught and retried")

    print("\n✓ All tests passed!")