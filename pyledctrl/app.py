"""
Main application class for PyLedCtrl
"""

from __future__ import print_function

import baker
import os
import subprocess
import sys

from pyledctrl.compiler import BytecodeCompiler
from pyledctrl.config import DEFAULT_BAUD
from pyledctrl.upload import BytecodeUploader
from pyledctrl.utils import error, get_serial_port_filename, \
    get_serial_connection

pyledctrl = baker.Baker()


@pyledctrl.command(shortopts=dict(output="o"))
def compile(filename, output=None):
    """\
    Compiles a LedCtrl source file to a bytecode file.

    :param filename: The name of the source file to compile.
    :param output: The name of the output file. When omitted, it will be
        the same as the input file but the extension will be replaced with
        ``.bin``.
    """
    if output is None:
        base, _ = os.path.splitext(filename)
        output = base + ".bin"
    compiler = BytecodeCompiler()
    compiler.compile(filename, output)


@pyledctrl.command(shortopts=dict(port="p", baud="b"))
def connect(port=None, baud=DEFAULT_BAUD):
    """\
    Connects to the LedCtrl serial console.

    :param port: Specifies the port to which the device is attached.
    :param baud: Specifies the baud rate to use.
    """
    port = get_serial_port_filename(port)
    if os.path.exists(port):
        return subprocess.call(["screen", port, str(baud or DEFAULT_BAUD)])
    else:
        error("No such port: {0}".format(port), fatal=True)


@pyledctrl.command(shortopts=dict(port="p", baud="b"))
def upload(filename, port=None, baud=DEFAULT_BAUD):
    """\
    Uploads a compiled LedCtrl bytecode file to an attached device using
    a serial port.

    :param filename: The name of the file to upload
    :param port: Specifies the port to which the device is attached.
    :param baud: Specifies the baud rate to use.
    """
    port = get_serial_connection(port, baud)
    uploader = BytecodeUploader(port)
    uploader.upload_file(filename)


def main():
    sys.exit(pyledctrl.run())
