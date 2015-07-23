"""Compilation stages being used in the bytecode compiler."""

import os

from .contexts import FileWriterExecutionContext


class CompilationStage(object):
    """Compilation stage that can be executed during a course of compilation.

    Stages typically produce a particular kind of output file from one or more
    input files during the compilation. For instance, a compilation stage may
    take a source file with ``.led`` extension, interpret it using a compilation
    context and produce a raw bytecode file with ``.bin`` extension in the end.
    """

    def run(self):
        """Executes the compilation phase."""
        raise NotImplementedError

    def should_run(self):
        """Returns whether the compilation phase should be executed. Returning
        ``False`` typically means that the target of the compilation phase is
        up-to-date so there is no need to re-run the compilation phase.
        """
        raise NotImplementedError


class FileBasedCompilationStage(CompilationStage):
    """Abstract compilation phase that turns a set of input files into a set of
    output files. The phase is not executed if all the input files are older than
    all the output files.
    """

    def __init__(self):
        super(FileBasedCompilationStage, self).__init__()
        self.input_files = []
        self.output_files = []

    def should_run(self):
        input_files, output_files = self.input_files, self.output_files

        if not output_files:
            return False
        if any(not os.path.exists(output) for output in output_files):
            return True
        if not input_files:
            return False
        if any(not os.path.exists(input) for input in input_files):
            # Just return True so we will execute, and then we will bail out
            return True

        youngest_output = min(os.path.getmtime(output) for output in output_files)
        oldest_input = max(os.path.getmtime(input) for input in input_files)
        return oldest_input >= youngest_output


class SourceToBinaryCompilationStage(FileBasedCompilationStage):
    def __init__(self, input, output):
        super(SourceToBinaryCompilationStage, self).__init__()
        self.input_files.append(input)
        self.output_files.append(output)

    def run(self):
        assert len(self.input_files) == 1
        assert len(self.output_files) == 1

        with open(self.output_files[0], "wb") as output:
            context = FileWriterExecutionContext(output)
            with open(self.input_files[0]) as fp:
                code = compile(fp.read(), self.input_files[0], "exec")
                context.evaluate(code, add_end_command=True)
