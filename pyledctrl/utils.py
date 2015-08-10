"""Utility functions for PyLedCtrl."""

from __future__ import print_function

import glob
import shutil
import sys
import tempfile

from groundctrl.serial_port import SerialPort
from itertools import islice
from pyledctrl.config import DEFAULT_BAUD


def ensure_tuple(obj):
    """Ensures that the given object is a tuple. If it is not a tuple,
    returns a tuple containing the object only."""
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
    if the iterable is empty."""
    for item in iterable:
        return item
    raise ValueError("iterable is empty")


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

    def __init__(self, suffix="", prefix=tempfile.template, dir=None, keep=False):
        self.name = tempfile.mkdtemp(suffix, prefix, dir)
        self.keep = keep

    @classmethod
    def _cleanup(cls, name, warn_message=None):
        if not self.keep:
            shutil.rmtree(name)
        if warn_message is not None:
            warnings.warn(warn_message, ResourceWarning)

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
