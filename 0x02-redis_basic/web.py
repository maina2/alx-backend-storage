#!/usr/bin/env python3
"""
This module provides a function to fetch web page content
with Redis-based caching and URL access counting using decorators.
"""

import redis
import requests
from functools import wraps
from typing import Callable

r = redis.Redis()


def count_url_access(method: Callable) -> Callable:
    """Decorator to count how many times a URL is accessed."""
    @wraps(method)
    def wrapper(url: str) -> str:
        r.incr(f"count:{url}")
        return method(url)
    return wrapper


def cache_page(expiration: int = 10) -> Callable:
    """Decorator to cache page content in Redis for a given number of seconds."""
    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(url: str) -> str:
            cache_key = f"cache:{url}"
            cached = r.get(cache_key)
            if cached:
                return cached.decode('utf-8')
            result = method(url)
            r.setex(cache_key, expiration, result)
            return result
        return wrapper
    return decorator


@cache_page(expiration=10)
@count_url_access
def get_page(url: str) -> str:
    """
    Fetch the HTML content of a URL.

    This version uses decorators for caching and counting.

    Args:
        url: The URL to fetch.

    Returns:
        The HTML content of the page.
    """
    return requests.get(url).text