"""Utility functions for PyLedCtrl."""

from __future__ import print_function

import glob
import shutil
import sys
import tempfile

from itertools import islice, tee
from pyledctrl.config import DEFAULT_BAUD


def changed_indexes(seq1, seq2):
    """Compares two sequences and returns the indices where the two
    sequences are different.

    The two sequences are assumed to have the same length.

    When a sequence is ``None``, all the indices of the other sequence are
    returned.

    When both sequences are ``None``, an empty list is returned.

    Parameters:
        seq1 (Optional[Seq[object]]): the first sequence
        seq2 (Optional[Seq[object]]): the second sequence

    Returns:
        List[int]: a list containing the indices where the two sequences are
            different
    """
    if seq1 is None:
        return [] if seq2 is None else range(len(seq2))
    if seq2 is None:
        return range(len(seq1))

    assert len(seq1) == len(seq2)
    return [i for i in xrange(len(seq1)) if seq1[i] != seq2[i]]


def consecutive_pairs(iterable):
    """Given an iterable, returns a generator that generates consecutive
    pairs of items from the iterable.

    Parameters:
        iteable (Iterable): the iterable

    Yields:
        (object, object): pairs of consecutive items from the iterable
    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def ensure_tuple(obj):
    """Ensures that the given object is a tuple. If it is not a tuple,
    returns a tuple containing the object only.
    """
    return obj if isinstance(obj, tuple) else obj,


def error(message, fatal=False):
    """Prints an error message to stderr.

    :param message: The message to print
    :param fatal: Whether to terminate the script after the error message
    """
    print(message, file=sys.stderr)
    if fatal:
        sys.exit(1)


def first(iterable):
    """Returns the first element from the given iterable. Raises ``ValueError``
    if the iterable is empty.
    """
    for item in iterable:
        return item
    raise ValueError("iterable is empty")


def format_frame_count(frames, fps):
    """Formats a time instant given as the number of frames since T=0 into
    a conventional minutes:seconds+frames representation.

    Parameters:
        frames (int): the number of frames
        fps (int): the number of frames per second

    Returns:
        str: the formatted representation of the frame count
    """
    seconds, residual = divmod(frames, fps)
    minutes, seconds = divmod(seconds, 60)
    return "{minutes}:{seconds:02}+{residual:02}".format(
        minutes=int(minutes), seconds=int(seconds), residual=int(residual)
    )


def get_serial_port_filename(port=None):
    """Returns the serial port filename from the given string, handling
    defaults gracefully.

    :param port: the serial port, ``None`` means to use the first USB serial
        port
    """
    if port is None:
        ttyusb = glob.glob('/dev/ttyUSB*') + ["/dev/ttyUSB0"]
        return ttyusb[0]
    else:
        return str(port)


def get_serial_connection(port, baud=None):
    """Returns a serial connection object for the given port and baud rate,
    handling defaults gracefully.

    :param port: the serial port, ``None`` means to use the first USB serial
        port
    :param baud: the baud rate, ``None`` uses the default baud rate
    """
    # Lazy import. This is important since groundctrl is not a strict
    # dependency of pyledctrl
    from groundctrl.serial_port import SerialPort
    return SerialPort(port=get_serial_port_filename(port),
                      baud=baud or DEFAULT_BAUD)


def grouper(iterable, n):
    """Iterates over the given iterable in chunks of n items."""
    it = iter(iterable)
    while True:
        chunk = tuple(islice(it, n))
        if not chunk:
            return
        yield chunk


def iterbytes(fp):
    """Iterates over the bytes of a file-like object."""
    while True:
        b = fp.read(1)
        if not b:
            return
        yield b


def memoize(func):
    """Single-argument memoization decorator for a function. Caches the results
    of the function in a dictionary.
    """
    class memodict(dict):
        __slots__ = ()

        def __missing__(self, key):
            self[key] = ret = func(key)
            return ret

    return memodict().__getitem__


def parse_as_frame_count(value, fps):
    """Parses the given input string containing the representation of a time
    instant in the usual ``minutes:seconds+frames`` format into an absolute
    frame count.

    When the frame (residual) part after the ``+`` sign is omitted, it is
    assumed to be zero.

    When the minutes part before the ``:`` sign is omitted, it is also
    assumed to be zero.

    Parameters:
        value (str): the input string to parse
        fps (int): the number of frames per second

    Returns:
        int: the absolute frame count parsed out from the string
    """
    minutes, _, seconds = value.rpartition(":")
    minutes = float(minutes) if minutes else 0
    seconds, _, residual = seconds.partition("+")
    seconds = float(seconds) if seconds else 0
    residual = float(residual) if residual else 0
    return int((minutes * 60 + seconds) * fps + residual)


class _TemporaryDirectory(object):
    """Create and return a temporary directory.  This has the same
    behaviour as mkdtemp but can be used as a context manager.
    Backported from Python 3.x. For example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed.
    """

    # Handle mkdtemp raising an exception
    name = None
    _closed = False

    def __init__(self, suffix="", prefix=tempfile.template, dir=None,
                 keep=False):
        self.name = tempfile.mkdtemp(suffix, prefix, dir)
        self.keep = keep

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.name is not None and not self._closed:
            if not self.keep:
                shutil.rmtree(self.name)
            self._closed = True

try:
    from tempfile import TemporaryDirectory
except ImportError:
    TemporaryDirectory = _TemporaryDirectory
