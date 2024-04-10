"""Utility objects and functions for the compiler."""

from time import time
from typing import Any, Callable, Generic, Optional, TypeVar, Union, overload


T = TypeVar("T")


@overload
def get_timestamp_of(obj: Any) -> Optional[float]: ...


@overload
def get_timestamp_of(obj: Any, default_value: T = None) -> Union[float, T]: ...


def get_timestamp_of(obj, default_value=None):
    """Returns the timestamp of the given object if it is timestamped; returns
    the given default value otherwise.

    Parameters:
        obj : the object whose timestamp is to be returned
        default_value : the default timestamp to return if the object
            is not timestamped or if it has no timestamp

    Returns:
        object: the timestamp of the object or the default value if the object
            is not timestamped or if it has no timestamp
    """
    return getattr(obj, "timestamp", default_value)


def is_timestamped(obj: Any) -> bool:
    """Returns whether a given object is timestamped.

    An object is timestamped if it has a ``timestamp`` property that returns
    a UNIX timestamp.
    """
    return hasattr(obj, "timestamp")


class TimestampWrapper(Generic[T]):
    """Wrapper object that wraps another object and adds a ``timestamp``
    property to it to make it timestamped.
    """

    _wrapped: T
    """The object wrapped by this wrapper."""

    _timestamp: float
    """The timestamp associated to the object."""

    @classmethod
    def wrap(cls, wrapped: T, timestamp: Union[float, Callable[[], float]] = time):
        """Creates a new timestamped wrapper for the given wrapped object.

        Parameters:
            wrapped: the object to wrap
            timestamp: the timestamp added to the object. When it is a callable,
                it will be called to obtain the timestamp. The default value
                calls ``time.time()`` to add the current time.
        """
        if callable(timestamp):
            timestamp = timestamp()
            assert isinstance(timestamp, (int, float))
        return cls(wrapped, timestamp)

    def __init__(self, wrapped: T, timestamp: float):
        """Constructor.

        Parameters:
            wrapped: the object to wrap
            timestamp: the timestamp added to the object.
        """
        self._wrapped = wrapped
        self._timestamp = float(timestamp)

    def __getattr__(self, attr):
        return getattr(self._wrapped, attr)

    @property
    def wrapped(self) -> T:
        """The object wrapped by this wrapper."""
        return self._wrapped
