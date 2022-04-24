"""Utility functions for PyLedCtrl."""

import os
import sys

from itertools import tee
from typing import cast, Callable, Iterable, Tuple, TypeVar, overload


T = TypeVar("T")
T2 = TypeVar("T2")
Tup = TypeVar("Tup", bound="Tuple")


def consecutive_pairs(it: Iterable[T]) -> Iterable[Tuple[T, T]]:
    """Given an iterable, returns a generator that generates consecutive
    pairs of items from the iterable.

    Parameters:
        it: the iterable

    Yields:
        pairs of consecutive items from the iterable
    """
    a, b = tee(it)
    next(b, None)
    return zip(a, b)


@overload
def ensure_tuple(obj: Tup) -> Tup:
    ...


@overload
def ensure_tuple(obj: T) -> Tuple[T]:
    ...


def ensure_tuple(obj):
    """Ensures that the given object is a tuple. If it is not a tuple,
    returns a tuple containing the object only.
    """
    return (obj if isinstance(obj, tuple) else obj,)


def error(message: str, fatal: bool = False) -> None:
    """Prints an error message to stderr.

    Parameters:
        message: The message to print
        fatal: Whether to terminate the script after the error message
    """
    print(message, file=sys.stderr)
    if fatal:
        sys.exit(1)


def first(iterable: Iterable[T]) -> T:
    """Returns the first element from the given iterable.

    Raises:
        ValueError: if the iterable is empty.
    """
    for item in iterable:
        return item
    raise ValueError("iterable is empty")


def format_frame_count(frames: int, *, fps: int) -> str:
    """Formats a time instant given as the number of frames since T=0 into
    a conventional minutes:seconds+frames representation.

    Parameters:
        frames: the number of frames
        fps: the number of frames per second

    Returns:
        the formatted representation of the frame count
    """
    seconds, residual = divmod(frames, fps)
    minutes, seconds = divmod(seconds, 60)
    return "{minutes}:{seconds:02}+{residual:02}".format(
        minutes=int(minutes), seconds=int(seconds), residual=int(residual)
    )


_last_default = object()


def last(iterable: Iterable[T]) -> T:
    """Returns the last element from the given iterable.

    Raises:
        ValueError: if the iterable is empty
    """
    last = _last_default
    for last in iterable:
        pass
    if last is _last_default:
        raise ValueError("iterable is empty")
    else:
        return cast(T, last)


def memoize(func: Callable[[T], T2]) -> Callable[[T], T2]:
    """Single-argument memoization decorator for a function. Caches the results
    of the function in a dictionary.
    """

    class memodict(dict):
        __slots__ = ()

        def __missing__(self, key: T):
            self[key] = ret = func(key)
            return ret

    return memodict().__getitem__


def parse_as_frame_count(value: str, *, fps: int) -> int:
    """Parses the given input string containing the representation of a time
    instant in the usual ``minutes:seconds+frames`` format into an absolute
    frame count.

    When the frame (residual) part after the ``+`` sign is omitted, it is
    assumed to be zero.

    When the minutes part before the ``:`` sign is omitted, it is also
    assumed to be zero.

    Parameters:
        value: the input string to parse
        fps: the number of frames per second

    Returns:
        the absolute frame count parsed out from the string
    """
    minutes, _, seconds = value.rpartition(":")
    minutes = float(minutes) if minutes else 0
    seconds, _, residual = seconds.partition("+")
    seconds = float(seconds) if seconds else 0
    residual = float(residual) if residual else 0
    return int((minutes * 60 + seconds) * fps + residual)


def replace_extension(filename: str, ext: str) -> str:
    """Replaces the extension of the given filename with another one.

    Parameters:
        filename: the filename to modify
        ext: the desired extension of the file

    Returns:
        the new filename
    """
    base, _ = os.path.splitext(filename)
    return base + ext
