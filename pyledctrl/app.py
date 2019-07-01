"""Main application class for PyLedCtrl"""

from __future__ import print_function

import baker
import csv
import logging
import os
import subprocess
import sys

from pyledctrl.compiler import BytecodeCompiler
from pyledctrl.config import DEFAULT_BAUD
from pyledctrl.executor import Executor
from pyledctrl.upload import BytecodeUploader
from pyledctrl.utils import (
    error,
    get_serial_port_filename,
    get_serial_connection,
    parse_as_frame_count,
)

pyledctrl = baker.Baker()


@pyledctrl.command(
    shortopts=dict(output="o", keep="k", optimisation="O", verbose="v", shift="s")
)
def compile(filename, output=None, keep=False, optimisation=2, shift="", verbose=False):
    """\
    Compiles a LedCtrl source file to a bytecode file.

    :param filename: The name of the source file to compile.
    :param output: The name of the output file. When omitted, it will be
        the same as the input file but the extension will be replaced with
        ``.bin``.
    :param keep: Whether to keep intermediate files generated during
        compilation.
    :param optimisation: The optimisation level to use. 0 = no optimisation,
        1 = only basic optimisations, 2 = aggressive optimisation (default).
    :param shift: Time interval with which the time axis parsed from the
        input file should be shifted *to the left*. This means that, e.g.,
        a shift of ``2:00`` would mean that the output file will start at
        2 minutes into the input file. The duration must be specified as
        ``MIN:SEC+FRAMES`` where the minutes and the frames may be omitted.
    :param verbose: Whether to print verbose messages about what the
        compiler is doing.
    """
    if output is None:
        base, _ = os.path.splitext(filename)
        output = base + ".bin"

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING, format="%(message)s"
    )

    compiler = BytecodeCompiler(keep_intermediate_files=keep, verbose=verbose)
    compiler.optimisation_level = optimisation

    # TODO(ntamas): don't hardcode 100 fps here
    compiler.shift_by = parse_as_frame_count(shift, fps=100) if shift else 0
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


@pyledctrl.command(shortopts=dict(output="o"))
def dump(filename, output=None, keep=False):
    """\
    Dumps the LED lighting sequence of a LedCtrl source file.

    The output of this command will be a tab-separated list of timestamps
    (in seconds), red, green and blue components (between 0 and 255, inclusive)
    and a Boolean flag that denotes whether the entry represents an abrupt
    change or a fade.

    :param filename: The name of the source file to compile.
    :param output: The name of the output file. When omitted, it will be
        the standard output.
    """
    if output is None:
        output = sys.stdout
    else:
        output = open(output, "w")

    writer = csv.writer(output, dialect="excel-tab")

    def state_to_row(state):
        """Converts an ExecutorState_ object to the row that we want to
        write into the output file.
        """
        return [
            "%g" % state.timestamp,
            state.color.red,
            state.color.green,
            state.color.blue,
            state.is_fade,
        ]

    compiler = BytecodeCompiler(keep_intermediate_files=False)
    compiler.compile(filename)
    syntax_trees = compiler.output

    for syntax_tree in syntax_trees:
        executor = Executor()
        writer.writerow(state_to_row(executor.state))
        for state in executor.execute(syntax_tree):
            writer.writerow(state_to_row(state))
        writer.writerow([])


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
    sys.exit(0 if uploader.upload_file(filename) else 1)


def main():
    """Main entry point of the compiler."""
    sys.exit(pyledctrl.run())
