"""
Performance Logging Decorator

This module provides decorators for logging slow operations
to help identify performance bottlenecks.
"""

import time
import logging
from functools import wraps

logger = logging.getLogger("general")


def log_performance(threshold=1.0):
    """Log function execution time if it exceeds threshold (in seconds)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            if duration > threshold:
                logger.warning(
                    f"SLOW OPERATION: {func.__module__}.{func.__name__} took {duration:.2f}s",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration": duration,
                    }
                )
            return result
        return wrapper
    return decorator
