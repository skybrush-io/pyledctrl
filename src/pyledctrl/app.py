"""Main application class for PyLedCtrl"""

import csv
import sys

from .compiler import BytecodeCompiler
from .executor import Executor, unroll as unroll_sequence
from .utils import replace_extension

try:
    import click
except ImportError:
    print("You need to install pyledctrl with the 'cli' extra to use the")
    print("command line interface.")
    sys.exit(1)


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
def compile(filename, output, optimisation, progress, verbose):
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
    syntax_trees = compiler.compile(filename, output_format="ast")

    for syntax_tree in syntax_trees:
        sequence = Executor().execute(syntax_tree)
        if unroll:
            sequence = unroll_sequence(sequence)

        for state in sequence:
            writer.writerow(state_to_row(state))


def main():
    """Main entry point of the compiler."""
    cli()
