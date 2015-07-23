"""Utility functions for PyLedCtrl."""

from __future__ import print_function

import glob
import sys


from groundctrl.serial_port import SerialPort
from pyledctrl.config import DEFAULT_BAUD


def error(message, fatal=False):
    """Prints an error message to stderr.

    :param message: The message to print
    :param fatal: Whether to terminate the script after the error message
    """
    print(message, file=sys.stderr)
    if fatal:
        sys.exit(1)


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
