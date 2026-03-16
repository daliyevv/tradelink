"""
Common decorators for API endpoints and functions.
"""
from functools import wraps
from django.core.cache import cache


def cache_result(timeout=3600):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds (default: 1 hour)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def async_task(func):
    """
    Decorator to run function as async Celery task.
    
    Requires Celery to be configured.
    """
    from celery import shared_task
    
    @wraps(func)
    @shared_task
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper
