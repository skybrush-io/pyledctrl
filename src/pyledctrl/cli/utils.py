import csv

from typing import IO

from pyledctrl.compiler import BytecodeCompiler
from pyledctrl.executor import Executor, ExecutorState, unroll as unroll_sequence

__all__ = ("execute_and_write_tabular",)


def execute_and_write_tabular(filename: str, output: IO[str], unroll: bool = False):
    """Executes some bytecode held in a given input file and dumps the
    evaluated bytecode in human-readable format to a stream.

    Parameters:
        filename: name of the input file that holds the bytecode
        output: stream to dump the result to
        unroll: whether to sample the bytecode at regular intervals instead of
            showing relevant timestamps only
    """
    writer = csv.writer(output, dialect="excel-tab")

    def state_to_row(state: ExecutorState):
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
