"""Compilation stages being used in the bytecode compiler."""

import os

from abc import ABCMeta, abstractmethod, abstractproperty
from contextlib import closing
from decimal import Decimal

from .ast import Comment
from .contexts import ExecutionContext
from .errors import CompilerError
from .utils import get_timestamp_of, TimestampedLineCollector, UnifiedTimeline

from pyledctrl.logger import log
from pyledctrl.parsers.bytecode import BytecodeParser
from pyledctrl.parsers.sunlite import (
    SunliteSuiteSceneFileParser,
    SunliteSuiteSwitchFileParser,
    FX,
    EasyStepTimeline,
)
from pyledctrl.utils import (
    changed_indexes,
    consecutive_pairs,
    first,
    format_frame_count,
)


class CompilationStageExecutionEnvironment:
    """Execution environment of compilation stages that contains a few
    functions that the stages may use to access functionality of the
    compiler itself.
    """

    def __init__(self, compiler):
        """Constructor.

        Parameters:
            compiler (BytecodeCompiler): the compiler that owns this
                environment
        """
        self._compiler = compiler

    log = log
    warn = log.warn


class CompilationStage(metaclass=ABCMeta):
    """Compilation stage that can be executed during a course of compilation.

    Stages typically produce a particular kind of output file from one or more
    input files during the compilation. For instance, a compilation stage may
    take a source file with ``.led`` extension, interpret it using a
    compilation context and produce a raw bytecode file with ``.bin``
    extension in the end.
    """

    label = "compiling..."

    @abstractmethod
    def run(self, environment):
        """Executes the compilation phase.

        Parameters:
            environment (CompilationStageExecutionEnvironment): the execution
                environment of the compilation stage, providing useful
                functions for printing warnings etc
        """
        raise NotImplementedError

    @abstractmethod
    def should_run(self):
        """Returns whether the compilation phase should be executed. Returning
        ``False`` typically means that the target of the compilation phase is
        up-to-date so there is no need to re-run the compilation phase.
        """
        raise NotImplementedError


class DummyStage(CompilationStage):
    """Dummy stage that does nothing on its own."""

    def run(self, environment):
        """Inherited."""
        pass

    def should_run(self):
        """Inherited."""
        return True


class FileSourceMixin(metaclass=ABCMeta):
    """Mixin class for compilation stages that assume that the source of
    the compilation stage is a set of files.
    """

    @abstractproperty
    def input_files(self):
        """The names of the input files of this compilation stage."""
        raise NotImplementedError

    @property
    def oldest_input_file_timestamp(self):
        """Returns the timestamp of the oldest input file or positive
        infinity if there are no input files. Raises an error if at least one
        input file is missing (i.e. does not exist).
        """
        input_files = self.input_files
        if not input_files:
            return float("inf")
        if any(not os.path.exists(filename) for filename in input_files):
            raise ValueError("a required input file is missing")
        return max(os.path.getmtime(filename) for filename in input_files)


class FileTargetMixin(metaclass=ABCMeta):
    """Mixin class for compilation stages that assume that the target of
    the compilation stage is a set of files.
    """

    @abstractproperty
    def output_files(self):
        """The names of the output files of this compilation stage."""
        raise NotImplementedError

    @property
    def youngest_output_file_timestamp(self):
        """Returns the timestamp of the youngest output file, positive
        infinity if there are no output files, or negative infinity if at
        least one output file is missing (i.e. does not exist).
        """
        output_files = self.output
        if not output_files:
            return float("-inf")
        if any(not os.path.exists(filename) for filename in output_files):
            return float("inf")
        return min(os.path.getmtime(filename) for filename in output_files)


class ObjectSourceMixin(metaclass=ABCMeta):
    """Mixin class for compilation stages that assume that the source of
    the compilation stage is an in-memory object.
    """

    @abstractproperty
    def input(self):
        """Returns the input object or the input stage on which this stage
        depends.
        """
        raise NotImplementedError

    @property
    def input_object(self):
        """Returns the input object on which this stage depends. If the stage
        depends on the output of another stage, this property will return the
        output object of the other stage.
        """
        inp = self.input
        if isinstance(inp, ObjectTargetMixin):
            return inp.output_object
        else:
            return inp


class ObjectTargetMixin(metaclass=ABCMeta):
    """Mixin class for compilation stages that assume that the target of
    the compilation stage is an in-memory object.
    """

    @abstractproperty
    def output(self):
        """THe output object of the compilation stage."""
        raise NotImplementedError

    @property
    def output_object(self):
        """Returns the output object of this stage. If the output object
        happens to be the same as the input object, and the input
        depends on the output of another stage, this property will return the
        output object of the other stage.
        """
        output = self.output
        if isinstance(output, ObjectTargetMixin):
            return output.output_object
        else:
            return output


class FileToObjectCompilationStage(
    CompilationStage, FileSourceMixin, ObjectTargetMixin
):
    """Abstract compilation phase that turns a set of input files into an
    in-memory object. This phase is executed unconditionally.
    """

    def should_run(self):
        """Whether this compilation step should be executed."""
        return True


class ObjectToFileCompilationStage(
    CompilationStage, ObjectSourceMixin, FileTargetMixin
):
    """Abstract compilation phase that turns an in-memory object into a set of
    output files. This phase is executed unconditionally if the in-memory
    object is not timestamped (i.e. does not have a ``timestamp`` property);
    otherwise it is executed if the timestamp of the input object is larger
    than the timestamps of any of the output objects.
    """

    def should_run(self):
        """Whether this compilation step should be executed.

        The compilation step is executed if the timestamp of the input
        object is later than the timestamp of the youngest output file.
        """
        input_timestamp = get_timestamp_of(
            self.input_object, default_value=float("inf")
        )
        return input_timestamp >= self.youngest_output_file_timestamp


class ObjectToObjectCompilationStage(
    CompilationStage, ObjectSourceMixin, ObjectTargetMixin
):
    """Abstract compilation phase that transforms an in-memory object into
    another in-memory object. This phase is executed unconditionally.
    """

    def should_run(self):
        """Whether this compilation step should be executed."""
        return True


class FileToFileCompilationStage(CompilationStage, FileSourceMixin, FileTargetMixin):
    """Abstract compilation phase that turns a set of input files into a set
    of output files. The phase is not executed if all the input files are
    older than all the output files.
    """

    def should_run(self):
        """Whether this compilation step should be executed.

        The compilation step is executed if the timestamp of the oldest
        input file is not earlier than the timestamp of the youngest
        output file.
        """
        youngest_output = self.youngest_output_file_timestamp
        oldest_input = self.oldest_input_file_timestamp
        return oldest_input >= youngest_output


class RawBytesToASTObjectCompilationStage(ObjectToObjectCompilationStage):
    """Abstract compilation stage that turns raw bytes containing the input
    in some input format into an in-memory abstract syntax tree.
    """

    label = "reading..."

    def __init__(self, input: bytes):
        """Constructor.

        Parameters:
            input: the raw bytes containing the input
        """
        super().__init__()
        self._input = input
        self._output = None

    @property
    def input(self):
        """Inherited."""
        return self._input

    @property
    def output(self):
        """Inherited."""
        return self._output

    def run(self, environment):
        self._output = self._create_output(self.input_object, environment)

    @abstractmethod
    def _create_output(self, input, environment):
        raise NotImplementedError


class LEDSourceCodeToASTObjectCompilationStage(RawBytesToASTObjectCompilationStage):
    """Compilation stage that turns Python source code given as raw bytes into
    an abstract syntax tree representation of the LED controller program in memory.
    """

    def _create_output(self, input, environment):
        context = ExecutionContext()
        code = compile(input, "<<bytecode>>", "exec")
        context.evaluate(code, add_end_command=True)
        return context.ast


class BytecodeToASTObjectCompilationStage(RawBytesToASTObjectCompilationStage):
    """Compilation stage that turns compiled bytecode back into an abstract
    syntax tree representation of the LED controller program in memory.
    """

    def _create_output(self, input, environment):
        """Inherited."""
        return BytecodeParser().parse(input)


class JSONBytecodeToASTObjectCompilationStage(RawBytesToASTObjectCompilationStage):
    """Compilation stage that turns compiled bytecode in JSON format back into
    an abstract syntax tree representation of the LED controller program in
    memory.
    """

    def _create_output(self, input, environment):
        """Inherited."""
        from base64 import b64decode
        from json import loads

        try:
            input = loads(input)
        except Exception:
            raise CompilerError("input must be a JSON object")

        if not isinstance(input, dict):
            raise CompilerError("input must be a JSON object")

        if input.get("version") != 1:
            raise CompilerError("only version 1 is supported")

        input = b64decode(input.get("data", "").encode("ascii"))
        return BytecodeParser().parse(input)


class ASTOptimisationStage(ObjectToObjectCompilationStage):
    """Compilation stage that takes an in-memory abstract syntax tree and
    optimises it in-place.
    """

    label = "optimizing..."

    def __init__(self, ast, optimiser):
        """Constructor.

        Parameters:
            ast (Node): the root of the abstract syntax tree that the
                compiler will optimise.
            optimiser (ASTOptimiser): the optimiser to use
        """
        super(ObjectToObjectCompilationStage, self).__init__()
        self._ast = ast
        self.optimiser = optimiser

    @property
    def input(self):
        """Inherited."""
        return self._ast

    @property
    def output(self):
        """Inherited."""
        return self._ast

    def run(self, environment):
        """Inherited."""
        self.optimiser.optimise(self.input_object)


class ASTObjectToRawBytesCompilationStage(ObjectToObjectCompilationStage):
    """Abstract compilation stage that turns an in-memory abstract syntax tree
    into some output format as raw bytes.
    """

    label = "writing..."

    def __init__(self, input):
        """Constructor.

        Parameters:
            input: the in-memory abstract syntax tree
        """
        super().__init__()
        self._input = input
        self._output = None

    @property
    def input(self):
        """Inherited."""
        return self._input

    @property
    def output(self):
        """Inherited."""
        return self._output

    def run(self, environment):
        self._output = self._create_output(self.input_object, environment)

    @abstractmethod
    def _create_output(self, input, environment):
        raise NotImplementedError


class ASTObjectToBytecodeCompilationStage(ASTObjectToRawBytesCompilationStage):
    """Compilation stage that turns an in-memory abstract syntax tree from a
    file into an in-memory bytecode that can be written directly to an output
    file or stream.
    """

    def _create_output(self, input, environment):
        """Inherited."""
        return input.to_bytecode()


class ASTObjectToJSONBytecodeCompilationStage(ASTObjectToRawBytesCompilationStage):
    """Compilation stage that turns an in-memory abstract syntax tree from a
    file into a JSON file that contains the raw bytecode in base64-encoded
    format.
    """

    def _create_output(self, input, environment):
        """Inherited."""
        from base64 import b64encode
        from json import dumps

        bytecode = input.to_bytecode()
        return dumps(
            {"version": 1, "data": b64encode(bytecode).decode("ascii")}, indent=2
        ).encode("ascii")


class ASTObjectToLEDSourceCodeCompilationStage(ASTObjectToRawBytesCompilationStage):
    """Compilation stage that turns an in-memory abstract syntax tree back into a
    (functionally equivalent) ``.led`` file.
    """

    def _create_output(self, input, environment):
        """Inherited."""
        output = input.to_led_source().encode("utf-8")
        if output:
            output += b"\n"
        return output


class ParsedSunliteScenesToPythonSourceCompilationStage(
    ObjectToFileCompilationStage
):  # noqa

    # TODO(ntamas): make these configurable
    FPS = Decimal(100)
    PYRO_THRESHOLD = 220
    PYRO_MASTER_CHANNEL = 6

    def __init__(self, input, output_template=None, start_at=0):
        """Constructor.

        Parameters:
            input: the parsed Sunlite Suite scene files
            output_template (str): template that defines how to derive the
                names of the output files, given the ID of an FX. Must
                contain a single ``{}`` token to identify the place where
                the FX ID should be inserted into.
            start_at (int): number of frames where the timeline of the
                output should start, in the timeline of the input files.
                E.g., setting this to ``200`` would mean that the output
                starts at 2 seconds into the input timelines, assuming
                100 frames per second.
        """
        super(ParsedSunliteScenesToPythonSourceCompilationStage, self).__init__()

        self._input = input

        if output_template is None:
            base, _ = os.path.splitext(input)
            output_template = base + "_{}.led"
        self._output_template = output_template
        self._outputs = None
        self._outputs_by_ids = None
        self._start_at = Decimal(start_at)

    @ObjectToFileCompilationStage.input.getter
    def input(self):
        """Inherited."""
        return self._input

    @ObjectToFileCompilationStage.output_files.getter
    def output_files(self):
        """Inherited."""
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
            for _, _, input_file in self.input_object
            for fx in input_file.fxs
        }
        self._outputs = sorted(self._outputs_by_ids.values())

    def _format_frame_count_as_time(self, frames):
        formatted_frames = format_frame_count(frames, fps=self.FPS)
        return "{formatted_frames} ({frames} frames)".format(
            formatted_frames=formatted_frames, frames=frames
        )

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
        if not all(
            channel.timeline.has_same_instants(timeline) for channel in channels
        ):
            raise RuntimeError(
                "channel merging is supported only if all the "
                "channels share the same timeline"
            )

        # Run the steps and maintain a list containing the current state of
        # each channel
        result = UnifiedTimeline()
        for index, time in enumerate(timeline.instants):
            steps = [channel.timeline.steps[index] for channel in channels]
            result.add(
                time, tuple(step.value if step is not None else 0 for step in steps)
            )

        # TODO: if first time instant is not at zero time, insert a fake
        # entry.
        if timeline.instants[0].time != 0:
            self.env.warn("First time step does not start at T=0")

        return result

    def run(self, environment):
        """Inherited."""
        # input_object is a sequence containing [(shift, size, scene_file)]
        # pairs such that the given scene_file has to be inserted into the
        # 'global' timeline after looping it to the given size and shifting
        # it by the given amount from t=0

        self.fx_map = {}
        self.env = environment

        try:
            # Process each single scene and build the global timeline
            for shift, size, scene_file in self.input_object:
                self._process_single_scene_file(scene_file, shift=shift, trim=size)

            # For each FX...
            for fx_id in sorted(self.fx_map.keys()):
                fx = self.fx_map[fx_id]

                # Merge the channels of the FX into a common timeline. The
                # result is a list containing pairs of time instants and
                # corresponding channel values for each channel (light and
                # pyro)
                merged_channels = self._merge_channels(fx.channels)

                # Insert the extra pyro master channel. Pyro channels are
                # indexed from zero, so PYRO_MASTER_CHANNEL = 6 means that
                # there will be at least seven pyro channels, and the
                # last one will be 1 about one second before at least one
                # other pyro channel turns 1
                merged_channels.ensure_min_channel_count(
                    self.PYRO_MASTER_CHANNEL + 3 + 1
                )
                prev_pyro, prev_active = None, False
                pyro_master_on = []
                for time, all_channels in merged_channels:
                    color, pyro = self._split_channels(all_channels)
                    if pyro == prev_pyro:
                        continue

                    active = any(v >= self.PYRO_THRESHOLD for v in pyro)
                    if active and not prev_active:
                        new_time = max(time.time - int(self.FPS), 0)
                        pyro_master_on.append((new_time, None))
                    elif not active and prev_active:
                        new_time = time.time + int(self.FPS)
                        pyro_master_on[-1] = (pyro_master_on[-1][0], new_time)

                    prev_active = active

                for start, end in pyro_master_on:
                    merged_channels.set_channel_value_in_range(
                        start, end, self.PYRO_MASTER_CHANNEL + 3, 255
                    )

                # Now that we are done with the merged channels, we can
                # apply the time shift that was specified at construction
                # time
                merged_channels.shift_to_left(self._start_at)

                # Write the result into the corresponding output file
                output_file = self.output_files_by_ids[fx.id]
                with open(output_file, "w") as fp:
                    self._dump_fx_to_file(fx, fp, merged_channels)
        finally:
            self.fx_map = None
            self.env = None

    def _process_single_scene_file(self, scene_file, shift=0, trim=None):
        """Processes the contents of a single Sunlite Suite scene file that is
        placed on the global timeline with the given shift.

        Parameters:
            scene_file (SceneFile): the parsed Sunlite Suite scene file
            shift (int): the index of the frame where the parsed Sunlite Suite
                scene file starts on the global timeline
            trim (Optional[int]): the index of the frame in the parsed Sunlite
                Suite scene file where the processing ends. The part of the
                timeline in the input file after the trim position is ignored.
                If the trim position does not have an exact value specification
                for the channels, the surrounding values will be interpolated
                linearly. ``None`` means not to trim the input file.
        """
        filename = scene_file.filename
        log.info("Processing scene file: {0}".format(filename))

        for fx_in_scene_file in scene_file.fxs:
            # Get the FX object that we will merge the FX from the scene
            # file into
            fx = self.fx_map.get(fx_in_scene_file.id)
            if fx is None:
                fx = FX()
                fx.id = fx_in_scene_file.id
                self.fx_map[fx.id] = fx

            # Add markers to the FX object so we know where this scene starts
            # and ends
            fx.add_marker(
                shift,
                "{0!r} starts at {1}".format(
                    filename, self._format_frame_count_as_time(shift)
                ),
            )

            # Compare the list of channels in our FX object and in the
            # FX object from the scene file. If there are any channels in
            # the FX of the file that we don't have, create them with our
            # global timeline.
            for channel in fx_in_scene_file.channels:
                max_index = channel.index + 1
                for extra_index in range(len(fx.channels), max_index):
                    fx.add_channel(EasyStepTimeline(fps=100))

            # Okay, great. Now we need to merge the timeline and steps of each
            # channel in the FX of the scene file into our FX, shifted
            # appropriately
            seen_indexes, timeline = set(), None
            for channel_in_scene_file in fx_in_scene_file.channels:
                our_channel = fx.channels[channel_in_scene_file.index]
                our_timeline = our_channel.timeline
                our_fps = our_timeline.fps

                timeline = channel_in_scene_file.timeline.scaled_to_fps(our_fps)
                timeline.loop_until(trim)
                timeline.shift(by=shift)

                our_timeline.merge_from(timeline)

                seen_indexes.add(channel_in_scene_file.index)

            # For any channel that was not in the scene file being processed
            # but is present in our merged FX object, we also need to extend
            # its timeline to make it stay compatible with the remaining
            # channels. We arbitrarily use the last timeline seen from the
            # scene file as a "template".
            for our_channel in fx.channels:
                if our_channel.index not in seen_indexes:
                    our_timeline = our_channel.timeline
                    our_timeline.merge_from(timeline)

    def _dump_fx_to_file(self, fx, fp, merged_channels):
        """Processes a single FX component from the merged Sunlite Suite
        stage files and writes the corresponding bytecode into the given
        file-like object.

        Parameters:
            fx: the FX component object
            fp (file): the file-like obejct to write the bytecode into
        """
        if fx.name:
            comment = Comment(value="{0!r} starts here".format(fx.name))
            fp.write(comment.to_led_source())

        # The bytecode generated by the loop below will be very
        # inefficient; e.g., if the same colors belong to two consecutive
        # steps, they could be merged, but the compiler won't do this.
        # It is up to an optimization step that comes later.

        # Create a "line collector" object that is responsible for printing
        # the appropriate commands to the output file and insert the
        # markers at the right places between lines
        lines = TimestampedLineCollector(out=fp, fps=self.FPS)
        for marker in fx.markers:
            marker.time -= self._start_at
            comment = Comment(value=marker.value)
            lines.add_marker(comment.to_led_source(), time=marker.time)

        with closing(lines):
            channel_iter = consecutive_pairs(merged_channels)

            last_color, last_pyro = None, None

            # Sequence is:
            # 1. We are at t=time.time, with color=channels.color
            # 2. We wait for time.wait
            # 3. We fade into color=next_channels.color with next_time.fade

            for (time, channels), (next_time, next_channels) in channel_iter:
                # Separate color and pyro channels
                color, pyro = self._split_channels(channels)

                # We are at 'time'. First, we handle the pyro channels.
                # Check whether any pyro channels have changed since the
                # previous step
                changed_pyro_channels = [ch for ch in changed_indexes(last_pyro, pyro)]

                if changed_pyro_channels:
                    # Validate the pyro channels; they should always be either
                    # 0 or 255. If this is not the case, it may be that
                    # something is messed up in the input file
                    if any(value not in (0, 255) for value in pyro):
                        self.env.warn(
                            "Pyro channel values are invalid at frame {0.time}"
                            " for FX {1}: {2!r}".format(time, fx.id, list(pyro))
                        )

                    if len(changed_pyro_channels) == 1:
                        # Only one pyro channel changed so we can generate a
                        # pyro_enable() or pyro_disable() command
                        changed = changed_pyro_channels[0]
                        if pyro[changed] >= self.PYRO_THRESHOLD:
                            pyro_command = "pyro_enable({0})".format(changed)
                        else:
                            pyro_command = "pyro_disable({0})".format(changed)
                    else:
                        # More than one channel changed so we generate a
                        # pyro_set_all() command
                        enabled_pyro_channels = [
                            index
                            for index, value in enumerate(pyro)
                            if value >= self.PYRO_THRESHOLD
                        ]
                        if enabled_pyro_channels:
                            pyro_command = "pyro_set_all({0})".format(
                                ", ".join(map(str, enabled_pyro_channels))
                            )
                        else:
                            pyro_command = "pyro_clear()"

                    lines.add(pyro_command)
                    last_pyro = pyro

                # We need to ensure that the current color is the one specified
                # in the time step if it is different from the color that we
                # have emitted the last time.
                time_to_wait = next_time.time - time.time - next_time.fade
                if time_to_wait != time.wait:
                    self.env.warn(
                        "Jump in timeline from frame {0} to frame {1}"
                        " in FX {2}".format(time.end, next_time.time, fx.id)
                    )
                already_waited = False
                if last_color != color:
                    command = "set_color({r}, {g}, {b}, duration=@DT@)".format(**color)
                    if next_time.fade == 0:
                        lines.add(command, time_to_wait)
                        already_waited = True
                    else:
                        lines.add(command)
                    last_color = color

                if next_time.fade > 0:
                    # Add an instruction to fade from the start color to the
                    # next color
                    next_color, _ = self._split_channels(next_channels)
                    lines.add(
                        "fade_to_color({r}, {g}, {b}, duration=@DT@)".format(
                            **next_color
                        ),
                        next_time.fade,
                    )
                    last_color = next_color

                if time_to_wait > 0 and not already_waited:
                    # Wait for the specified amount of time if we did not wait
                    # already in the set_color() command emitted above
                    lines.add("sleep(duration=@DT@)", time_to_wait)

        if fx.name:
            comment = Comment(value="{0!r} ends here".format(fx.name))
            fp.write(comment.to_led_source() + "\n")

    def _split_channels(self, all_channels):
        """Given the values of all the channels at a given time instant,
        separates them into color and pyro channels.

        Parameters:
            all_channels (List[int]): the list of channel values

        Returns:
            (Dict, List[int]): a dictionary with keys ``r``, ``g`` and ``b``
                for the values of the color channels, and a list containing
                the values of the pyro channels.
        """
        r, g, b = all_channels[:3]
        return dict(r=r, g=g, b=b), all_channels[3:]


class SunliteSceneParsingStage(FileToObjectCompilationStage):
    label = "parsing..."

    def __init__(self, input, shift=0):
        super(SunliteSceneParsingStage, self).__init__()

        self._input = input
        self._output = None
        self._shift = float(shift)

    @FileToObjectCompilationStage.input_files.getter
    def input_files(self):
        """Inherited."""
        return [self._input]

    @FileToObjectCompilationStage.output.getter
    def output(self):
        """Inherited."""
        return self._output

    def _parse(self):
        """Parses the input file and returns the parsed representation."""
        with open(self._input, "rb") as fp:
            result = SunliteSuiteSceneFileParser().parse(fp)
        if self._shift:
            result.shift(self._shift)
        return result

    def run(self, environment):
        """Inherited."""
        self._output = self._parse()


class SunliteSwitchParsingStage(FileToObjectCompilationStage):
    label = "parsing..."

    def __init__(self, input):
        super(SunliteSwitchParsingStage, self).__init__()

        self._input = input
        self._output = None

    @FileToObjectCompilationStage.input_files.getter
    def input_files(self):
        """Inherited."""
        return [self._input]

    @FileToObjectCompilationStage.output.getter
    def output(self):
        """Inherited."""
        return self._output

    def _parse(self):
        """Parses the input file and returns the parsed representation."""
        with open(self._input, "rb") as fp:
            return SunliteSuiteSwitchFileParser().parse(fp)

    def run(self, environment):
        """Inherited."""
        self._output = self._parse()