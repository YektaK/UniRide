"""
Design Patterns

Reusable design pattern implementations.
"""

import threading


class SingletonMeta(type):
    """
    Thread-safe Singleton metaclass.

    Uses threading.Lock to ensure only one instance is created
    even under concurrent access from multiple threads.

    Usage:
        class MyClass(metaclass=SingletonMeta):
            pass
    """
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # Double-checked locking for performance
        if cls not in cls._instances:
            with cls._lock:
                # Re-check after acquiring lock
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


__all__ = ["SingletonMeta"]
