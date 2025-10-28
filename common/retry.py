"""
Retry logic with exponential backoff.

Provides a decorator to automatically retry functions that fail due to
transient errors (e.g., network issues, API rate limits).
"""

import time
import functools
from typing import Callable, Type, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first try)
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry (exponential backoff)
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(APIError,))
        def fetch_data(symbol):
            return api.get_data(symbol)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    attempt += 1
                    
                    # If this was the last attempt, re-raise
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Log retry
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error(f"on_retry callback failed: {callback_error}")
                    
                    # Wait before retry
                    time.sleep(current_delay)
                    
                    # Increase delay for next retry (exponential backoff)
                    current_delay *= backoff
            
        return wrapper
    return decorator


def retry_with_timeout(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    timeout: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Retry decorator with timeout per attempt.
    
    Similar to retry() but adds a timeout for each attempt.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        timeout: Timeout in seconds per attempt
        exceptions: Exception types to retry on
    """
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Function call timed out after {timeout}s")
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    # Set timeout alarm
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(int(timeout))
                    
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        # Cancel alarm
                        signal.alarm(0)
                
                except (TimeoutError, *exceptions) as e:
                    attempt += 1
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator
