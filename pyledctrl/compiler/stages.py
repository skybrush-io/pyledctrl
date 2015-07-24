"""Compilation stages being used in the bytecode compiler."""

import heapq
import os

from itertools import groupby
from operator import itemgetter
from pyledctrl.compiler.contexts import FileWriterExecutionContext
from pyledctrl.parsers.sunlite import SunliteSuiteParser, Time


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


class PythonSourceToBytecodeCompilationStage(FileBasedCompilationStage):
    def __init__(self, input, output):
        super(PythonSourceToBytecodeCompilationStage, self).__init__()
        self._input = input
        self._output = output

    @FileBasedCompilationStage.input_files.getter
    def input_files(self):
        return [self._input]

    @FileBasedCompilationStage.output_files.getter
    def output_files(self):
        return [self._output]

    def run(self):
        with open(self._output, "wb") as output:
            context = FileWriterExecutionContext(output)
            with open(self._input) as fp:
                code = compile(fp.read(), self.input_files[0], "exec")
                context.evaluate(code, add_end_command=True)


class SunliteSceneToPythonSourceCompilationStage(FileBasedCompilationStage):
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

    @FileBasedCompilationStage.input_files.getter
    def input_files(self):
        return [self._input]

    @FileBasedCompilationStage.output_files.getter
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
        values. Time is represented as a ``pyledctrl.parsers.sunlite.Time``
        object where the ``wait`` property is set to the delay from the
        current time point to the *next* time point that will come up in the
        sequence, and the ``fade`` property is set to ``True`` if the transition
        should be a fade from the *previous* value."""

        # Extract all the steps from the timelines of the channels and sort them
        # by time
        steps = []
        for index, channel in enumerate(channels):
            steps.extend((time_obj.time, index, time_obj, step)
                         for time_obj, step in channel.timeline.iteritems())
        steps.sort()

        # Run the steps and maintain a list containing the current state of
        # each channel
        channel_values = [None] * len(channels)
        prev_time_obj = Time()
        for time, steps_at_same_time in groupby(steps, key=itemgetter(0)):
            # Calculate the time that has passed since the previous call
            # to yield
            prev_time_obj.wait = time - prev_time_obj.time
            if prev_time_obj.wait > 0:
                yield prev_time_obj, tuple(channel_values)
                prev_time_obj.time = time

            # Now perform the steps.
            # We will ask for a faded transition if at least one of the channels
            # requests a faded transition (as we cannot fade LED components
            # separately)
            for _, index, time_obj, step in steps_at_same_time:
                channel_values[index] = step
                prev_time_obj.fade = prev_time_obj.fade or time_obj.fade

        # Yield the final state of the channels
        prev_time_obj.wait = 0
        yield prev_time_obj, tuple(channel_values)

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
        for time, steps_by_channels in self._merge_channels(fx.channels):
            r, g, b = tuple(step.value if step else 0
                            for step in steps_by_channels)
            params = {
                "cmd": "fade_to_color" if time.fade else "set_color",
                "r": r, "g": g, "b": b,
                "dt": time.wait / 25.0
            }
            fp.write("{cmd}({r}, {g}, {b}, duration={dt})\n".format(**params))
