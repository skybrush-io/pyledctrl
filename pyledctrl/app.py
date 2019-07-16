"""Main application class for PyLedCtrl"""

from __future__ import print_function

import click
import csv
import os
import subprocess
import sys

from .compiler import BytecodeCompiler
from .config import DEFAULT_BAUD
from .executor import Executor, unroll as unroll_sequence
from .upload import BytecodeUploader
from .utils import (
    error,
    get_serial_port_filename,
    get_serial_connection,
    parse_as_frame_count,
)


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "-o",
    "--output",
    metavar="FILENAME",
    help="name of the output file. When omitted, it will be "
    "the same as the input file but the extension will be replaced with "
    ".bin",
    default=None,
)
@click.option(
    "--keep/--no-keep",
    help="whether to keep intermediate files generated during compilation",
    default=False,
)
@click.option(
    "-O",
    "--optimise",
    "optimisation",
    type=int,
    metavar="LEVEL",
    help="the optimisation level to use. 0 = no optimisation, "
    "1 = only basic optimisations, 2 = aggressive optimisation (default).",
    default=2,
)
@click.option(
    "-s",
    "--shift",
    metavar="TIME",
    type=str,
    help="Time interval with which the time axis parsed from the "
    "input file should be shifted *to the left*. This means that, e.g., "
    "a shift of ``2:00`` would mean that the output file will start at "
    "2 minutes into the input file. The duration must be specified as "
    "``MIN:SEC+FRAMES`` where the minutes and the frames may be omitted.",
    default="",
)
@click.option("-v", "--verbose", default=False, is_flag=True)
@click.argument("filename", required=True)
def compile(filename, output, keep, optimisation, shift, verbose):
    """Compiles a LedCtrl source file to a bytecode file.

    Takes a single input filename as its only argument.
    """
    if output is None:
        base, _ = os.path.splitext(filename)
        output = base + ".bin"

    compiler = BytecodeCompiler(keep_intermediate_files=keep, verbose=verbose)
    compiler.optimisation_level = optimisation

    # TODO(ntamas): don't hardcode 25 fps here
    compiler.shift_by = parse_as_frame_count(shift, fps=25) if shift else 0
    compiler.compile(filename, output)


@cli.command()
@click.option(
    "-p",
    "--port",
    type=str,
    help="the port to which the device is attached",
    default=None,
)
@click.option(
    "-b", "--baud", type=int, help="the baud rate to use", default=DEFAULT_BAUD
)
def connect(port, baud):
    """Connects to the LedCtrl serial console."""
    port = get_serial_port_filename(port)
    if os.path.exists(port):
        return subprocess.call(["screen", port, str(baud or DEFAULT_BAUD)])
    else:
        error("No such port: {0}".format(port), fatal=True)


@cli.command()
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    help="name of the output file",
    default=sys.stdout,
)
@click.option(
    "-u",
    "--unroll/--no-unroll",
    help="unroll fades into individual color steps",
    default=False,
    is_flag=True,
)
@click.argument("filename", required=True)
def dump(filename, output, unroll):
    """\
    Dumps the LED lighting sequence of a LedCtrl source file.

    The output of this command will be a tab-separated list of timestamps
    (in seconds), red, green and blue components (between 0 and 255, inclusive)
    and a boolean flag that denotes whether the entry represents an abrupt
    change or a fade from the _previous_ step to the current one.
    """
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
        # writer.writerow(state_to_row(executor.state))

        sequence = executor.execute(syntax_tree)
        if unroll:
            sequence = unroll_sequence(sequence)

        for state in sequence:
            writer.writerow(state_to_row(state))


@cli.command()
@click.option(
    "-p",
    "--port",
    type=str,
    help="the port to which the device is attached",
    default=None,
)
@click.option(
    "-b", "--baud", type=int, help="the baud rate to use", default=DEFAULT_BAUD
)
@click.argument("filename", required=True)
def upload(filename, port, baud):
    """\
    Uploads a compiled LedCtrl bytecode file to an attached device using
    a serial port.

    Takes the name of the bytecode file to upload as its only argument.
    """
    port = get_serial_connection(port, baud)
    uploader = BytecodeUploader(port)
    sys.exit(0 if uploader.upload_file(filename) else 1)


def main():
    """Main entry point of the compiler."""
    cli()
