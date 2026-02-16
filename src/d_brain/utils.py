"""Utility functions for d-brain bot."""

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Raised when API rate limit is exceeded."""
    pass


async def handle_rate_limit(
    func: Callable[..., Coroutine[Any, Any, Any]], 
    *args, 
    delay: float = 1.0, 
    max_retries: int = 3,
    **kwargs
) -> Any:
    """
    Handle API rate limiting with exponential backoff.
    
    Args:
        func: Async function to call
        args: Arguments to pass to the function
        delay: Initial delay between retries (seconds)
        max_retries: Maximum number of retry attempts
        kwargs: Keyword arguments to pass to the function
    
    Returns:
        Result of the function call
        
    Raises:
        RateLimitException: If max retries reached
    """
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Check if it's a rate limit error (HTTP 429 or similar)
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                if attempt < max_retries:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {wait_time}s before retry..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries reached for rate limit error: {e}")
                    raise RateLimitException(f"Rate limit exceeded after {max_retries} retries: {e}")
            else:
                # Re-raise if it's not a rate limit error
                raise e

    # This should not be reached, but included for completeness
    raise RateLimitException(f"Function failed after {max_retries} retries")
