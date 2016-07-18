"""Compilation stages being used in the bytecode compiler."""

import os
import re

try:
    import cPickle as pickle     # for Python 2.x
except ImportError:
    import pickle                # for Python 3.x

from functools import partial
from pyledctrl.compiler.contexts import ExecutionContext
from pyledctrl.compiler.errors import InvalidDurationError, \
    InvalidASTFormatError
from pyledctrl.parsers.sunlite import SunliteSuiteParser
from pyledctrl.utils import first, grouper, iterbytes
from textwrap import dedent


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


class FileToObjectCompilationStage(CompilationStage):
    """Abstract compilation phase that turns a set of input files into an
    in-memory object. This phase is executed unconditionally.
    """

    @property
    def input_files(self):
        raise []

    def should_run(self):
        return True


class FileToFileCompilationStage(CompilationStage):
    """Abstract compilation phase that turns a set of input files into a set of
    output files. The phase is not executed if all the input files are older than
    all the output files.
    """

    @property
    def input_files(self):
        raise []

    @property
    def output_files(self):
        raise []

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


class PythonSourceToASTObjectCompilationStage(FileToObjectCompilationStage):
    """Compilation stage that turns a Python source file into an abstract
    syntax tree representation of the LED controller program in memory.
    """

    def __init__(self, input):
        super(PythonSourceToASTObjectCompilationStage, self).__init__()
        self._input = input
        self._output = None

    @FileToObjectCompilationStage.input_files.getter
    def input_files(self):
        return [self._input]

    @property
    def output(self):
        return self._output

    def run(self):
        context = ExecutionContext()
        with open(self._input) as fp:
            code = compile(fp.read(), self.input_files[0], "exec")
            context.evaluate(code, add_end_command=True)
            self._output = context.ast


class PythonSourceToASTFileCompilationStage(FileToFileCompilationStage):
    """Compilation stage that turns a Python source file into an abstract
    syntax tree representation of the LED controller program and saves this
    representation to permanent storage."""

    def __init__(self, input, output, id=None):
        super(PythonSourceToASTFileCompilationStage, self).__init__()
        self._input = input
        self._output = output
        self.id = id

    @FileToFileCompilationStage.input_files.getter
    def input_files(self):
        return [self._input]

    @FileToFileCompilationStage.output_files.getter
    def output_files(self):
        return [self._output]

    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, value):
        self._output = value

    def run(self):
        pickle_format, pickler = self._choose_pickler()
        with open(self._output, "wb") as output:
            output.write(b"# Format: {0}\n".format(pickle_format.encode("utf-8")))
            context = ExecutionContext()
            with open(self._input) as fp:
                code = compile(fp.read(), self.input_files[0], "exec")
                context.evaluate(code, add_end_command=True)
                pickler(context.ast, output)

    def _choose_pickler(self):
        return u"pickle", partial(pickle.dump, protocol=pickle.HIGHEST_PROTOCOL)


class ASTFileToOutputCompilationStage(FileToFileCompilationStage):
    """Abstract compilation stage that turns a pickled abstract syntax tree
    into some output file."""

    def __init__(self, input, output):
        super(ASTFileToOutputCompilationStage, self).__init__()
        self._input = input
        self._output = output

    def get_ast(self):
        """Returns the abstract syntax tree from the input file."""
        with open(self._input, "rb") as fp:
            ast_format = self._get_ast_format(fp.readline())
            if ast_format == "pickle":
                return self._get_ast_pickle(fp)
            else:
                raise InvalidASTFormatError(self._input, ast_format)

    def _get_ast_pickle(self, fp):
        return pickle.load(fp)

    @staticmethod
    def _get_ast_format(line):
        match = re.match("# Format: (.*)", line.decode("utf-8"))
        return match.group(1).lower() if match else None

    @FileToFileCompilationStage.input_files.getter
    def input_files(self):
        return [self._input]

    @FileToFileCompilationStage.output_files.getter
    def output_files(self):
        return [self._output]


class ASTFileToBytecodeCompilationStage(ASTFileToOutputCompilationStage):
    """Compilation stage that turns a pickled abstract syntax tree from a
    file into a bytecode file that can be uploaded to the Arduino using
    ``ledctrl upload``."""

    def run(self):
        ast = self.get_ast()
        with open(self._output, "wb") as output:
            output.write(ast.to_bytecode())


class ASTFileToProgmemHeaderCompilationStage(ASTFileToOutputCompilationStage):
    """Compilation stage that turns a pickled abstract syntax tree from a
    file into a header file that can be compiled into the ``ledctrl`` source code
    with an ``#include`` directive."""

    HEADER = dedent(
        """\
        /* This is an autogenerated file; do not edit */
        #include <avr/pgmspace.h>
        #include "bytecode_store.h"

        static const u8 _bytecode[] PROGMEM = {
        """)

    FOOTER = dedent(
        """\
        };

        PROGMEMBytecodeStore bytecodeStore(_bytecode);
        """)

    def run(self):
        ast = self.get_ast()
        with open(self._output, "w") as output:
            output.write(self.HEADER)
            with open(self._input, "rb") as fp:
                for bytes_in_row in grouper(ast.to_bytecode(), 16):
                    output.write("  {0},\n".format(
                        ", ".join("0x{:02x}".format(ord(b)) for b in bytes_in_row)
                    ))
            output.write(self.FOOTER)


class SunliteSceneToPythonSourceCompilationStage(FileToFileCompilationStage):
    def __init__(self, input, output_template=None):
        super(SunliteSceneToPythonSourceCompilationStage, self).__init__()

        self._input = input
        self._parsed_input = None

        if output_template is None:
            base, _ = os.path.splitext(input)
            output_template = base + "_{}.led"
        self._output_template = output_template
        self._outputs = None
        self._outputs_by_ids = None

    @FileToFileCompilationStage.input_files.getter
    def input_files(self):
        return [self._input]

    @FileToFileCompilationStage.output_files.getter
    def output_files(self):
        if self._outputs is None:
            self._validate_outputs()
        return self._outputs

    @property
    def output_files_by_ids(self):
        if self._outputs is None:
            self._validate_outputs()
        return self._outputs_by_ids

    def _validate_outputs(self):
        """Calculates the list of output files."""
        self._outputs_by_ids = {
            fx.id: self._output_template.replace("{}", fx.id)
            for fx in self.parsed_input.fxs
        }
        self._outputs = sorted(self._outputs_by_ids.values())

    @property
    def parsed_input(self):
        """Returns the parsed input file as a pyledctrl.parsers.sunlite.SceneFile
        object."""
        if self._parsed_input is None:
            self._parsed_input = self._parse()
        return self._parsed_input

    def _parse(self):
        """Parses the input file and returns the parsed representation."""
        with open(self._input, "rb") as fp:
            return SunliteSuiteParser().parse(fp)

    def _merge_channels(self, channels):
        """Merges multiple channels into a common timeline. Yields pairs
        containing the current time and a tuple of the corresponding channel
        values. It is assumed that all the channels share the same timeline
        object, otherwise the operation would be ambiguous if there are
        different fade or wait times for different channels.
        """
        if not channels:
            return

        timeline = first(channel.timeline for channel in channels)
        if not all(channel.timeline.has_same_instants(timeline) for channel in channels):
            raise RuntimeError("channel merging is supported only if all the "
                               "channels share the same timeline")

        # Run the steps and maintain a list containing the current state of
        # each channel
        for index, time in enumerate(timeline.instants):
            yield time, (channel.timeline.steps[index] for channel in channels)

    def run(self):
        for fx in self.parsed_input.fxs:
            output_file = self.output_files_by_ids[fx.id]
            with open(output_file, "w") as fp:
                self._process_single_fx(fx, fp)

    def _process_single_fx(self, fx, fp):
        """Processes a single FX component from the Sunlite Suite stage file
        and writes the corresponding bytecode into the given file-like object.

        :param fx: the FX component object
        :param fp: the file-like object to write the bytecode into
        """

        # TODO: the bytecode generated by the loop below will be very
        # inefficient; e.g., if the same colors belong to two consecutive
        # steps, they could be merged, but the compiler won't do this.
        # In the next version, we should generate an AST (abstract syntax
        # tree) at this compilation stage and then set up a set of AST
        # optimizers that make the bytecode more efficient

        prev_time = None
        for time, steps_by_channels in self._merge_channels(fx.channels):
            r, g, b = tuple(step.value if step else 0
                            for step in steps_by_channels)
            params = dict(r=r, g=g, b=b)
            if prev_time is None:
                # This is the first step; process time.wait only as time.fade
                # will be processed in the next iteration
                fp.write("set_color({r}, {g}, {b}, duration={dt})\n".format(
                    dt=time.wait / 25.0, **params))
            elif prev_time.fade == 0:
                fp.write("set_color({r}, {g}, {b}, duration={dt})\n".format(
                    dt=time.wait / 25.0, **params))
            elif prev_time.fade > 0:
                fp.write("fade_to_color({r}, {g}, {b}, duration={dt})\n".format(
                    dt=prev_time.fade / 25.0, **params))
                if time.wait > 0:
                    fp.write("sleep(duration={dt})\n".format(dt=time.wait / 25.0))
            else:
                raise InvalidDurationError(prev_time.fade + " frames")
            prev_time = time
