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
from .utils import error, replace_extension


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
    "-p",
    "--progress",
    default=False,
    is_flag=True,
    help="Show the progress of the compilation process with a progress bar.",
)
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print additional messages about the compilation process above the progress bar.",
)
@click.argument("filename", required=True)
def compile(filename, output, optimisation, shift, progress, verbose):
    """Compiles a LedCtrl source file to a bytecode file.

    Takes a single input filename as its only argument.
    """
    if output is None:
        output = replace_extension(filename, ".bin")

    compiler = BytecodeCompiler(
        optimisation_level=optimisation, progress=progress, verbose=verbose
    )
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
    from .utils import get_serial_port_filename

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

    The last column is omitted if `--unroll` is specified.
    """
    writer = csv.writer(output, dialect="excel-tab")

    def state_to_row(state):
        """Converts an ExecutorState_ object to the row that we want to
        write into the output file.
        """
        row = [
            "%g" % state.timestamp,
            state.color.red,
            state.color.green,
            state.color.blue,
        ]
        if not unroll:
            row.append(state.is_fade)
        return row

    compiler = BytecodeCompiler()
    syntax_trees = compiler.compile(filename)

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
    from .utils import get_serial_connection
    from .upload import BytecodeUploader

    port = get_serial_connection(port, baud)
    uploader = BytecodeUploader(port)
    sys.exit(0 if uploader.upload_file(filename) else 1)


def main():
    """Main entry point of the compiler."""
    cli()
