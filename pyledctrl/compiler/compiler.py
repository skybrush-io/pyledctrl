"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats."""

import os

from .errors import UnsupportedInputFileFormatError
from .stages import SourceToBinaryCompilationStage


class BytecodeCompiler(object):
    """Bytecode compiler that produces raw bytecode from input files in
    various formats."""

    def __init__(self):
        pass

    def compile(self, input_file, output_file):
        """Runs the compiler.

        :param input_file: the input file to compiler
        :type input_file: str
        :param output_file: the output file that the compiler will produce
        :type output_file: str

        :raises CompilerError: in case of a compilation error
        """
        plan = []
        self._collect_stages(input_file, output_file, plan)
        last_step = plan[-1] if plan else None

        for step in plan:
            if step == last_step or step.should_run():
                step.run()

    def _collect_stages(self, input_file, output_file, plan):
        """Collects the compilation stages that will turn the given input
        file into the given output file.

        :param input_file: the name of the input file
        :type input_file: str
        :param output_file: the name of the output file
        :type output_file: str
        :param plan: output argument where the collected stages will be
             appended to
        :type plan: list

        :raises UnsupportedInputFileFormatError: when the format of the input
            file is not known to the compiler
        """
        _, ext = os.path.splitext(input_file)
        ext = ext.lower()

        if ext == ".led":
            plan.append(SourceToBinaryCompilationStage(input_file, output_file))
        else:
            raise UnsupportedInputFileFormatError(ext)
