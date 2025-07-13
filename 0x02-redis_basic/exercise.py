#!/usr/bin/env python3
"""
This module provides a Cache class that interfaces with Redis to store
and retrieve data using unique keys. It also includes decorators to track
method call counts and store call history for debugging and analytics.
"""

import redis
import uuid
from typing import Union, Callable, Optional
from functools import wraps


def count_calls(method: Callable) -> Callable:
    """
    Decorator that counts how many times a method is called.

    The count is stored in Redis using the method’s qualified name.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        """Wrapper function that increments call count and calls method."""
        key = method.__qualname__
        self._redis.incr(key)
        return method(self, *args, **kwargs)
    return wrapper


def call_history(method: Callable) -> Callable:
    """
    Decorator that stores the history of inputs and outputs for a method.

    Inputs are stored in a list at '<qualname>:inputs' and
    outputs at '<qualname>:outputs' using Redis RPUSH.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        """Wrapper that logs input and output to Redis lists."""
        input_key = f"{method.__qualname__}:inputs"
        output_key = f"{method.__qualname__}:outputs"

        self._redis.rpush(input_key, str(args))

        output = method(self, *args, **kwargs)

        self._redis.rpush(output_key, str(output))
        return output
    return wrapper


class Cache:
    """
    A Cache class for storing data in Redis using unique keys.

    This class connects to a Redis instance, flushes the database on
    initialization, and provides methods to store and retrieve data
    with optional format conversion. It also tracks method usage.
    """

    def __init__(self) -> None:
        """
        Initialize the Cache instance.

        Connects to the Redis server and flushes the database to start
        with a clean state.
        """
        self._redis = redis.Redis()
        self._redis.flushdb()

    @call_history
    @count_calls
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """
        Store data in Redis with a randomly generated UUID key.

        Args:
            data: The data to be stored. Can be of type str, bytes,
                  int, or float.

        Returns:
            A string representing the UUID key under which the data
            was stored.
        """
        key = str(uuid.uuid4())
        self._redis.set(key, data)
        return key

    def get(self,
            key: str,
            fn: Optional[Callable[[bytes], Union[str, int, float]]] = None
            ) -> Union[bytes, str, int, float, None]:
        """
        Retrieve data from Redis using a key, with optional conversion.

        Args:
            key: The key under which the data is stored.
            fn: Optional callable to convert the data (e.g., decode or cast).

        Returns:
            The retrieved data (converted if fn is provided), or None
            if the key does not exist.
        """
        data = self._redis.get(key)
        if data is None:
            return None
        return fn(data) if fn else data

    def get_str(self, key: str) -> Optional[str]:
        """
        Retrieve data from Redis and decode it as a UTF-8 string.

        Args:
            key: The key under which the data is stored.

        Returns:
            The decoded string, or None if the key does not exist.
        """
        return self.get(key, fn=lambda d: d.decode("utf-8"))

    def get_int(self, key: str) -> Optional[int]:
        """
        Retrieve data from Redis and convert it to an integer.

        Args:
            key: The key under which the data is stored.

        Returns:
            The converted integer, or None if the key does not exist.
        """
        return self.get(key, fn=lambda d: int(d))

    def replay(method: Callable) -> None:
        """
        Display the history of calls of a particular function.

        It prints:
        - The number of times the method was called
        - The list of input arguments
        - The corresponding outputs

        Args:
            method: The method whose history should be displayed.
        """
        r = redis.Redis()
        qualname = method.__qualname__

        call_count = r.get(qualname)
        print(f"{qualname} was called {int(call_count or 0)} times:")

        inputs = r.lrange(f"{qualname}:inputs", 0, -1)
        outputs = r.lrange(f"{qualname}:outputs", 0, -1)

        for input_bytes, output_bytes in zip(inputs, outputs):
            input_str = input_bytes.decode("utf-8")
            output_str = output_bytes.decode("utf-8")
            print(f"{qualname}(*{input_str}) -> {output_str}")