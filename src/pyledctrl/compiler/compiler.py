"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats.
"""

import os

from pathlib import Path
from typing import Any, Optional, Tuple

from .errors import CompilerError, UnsupportedInputFormatError
from .formats import InputFormat, InputFormatLike, OutputFormat, OutputFormatLike
from .optimisation import create_optimiser_for_level
from .plan import Plan
from .stages import (
    ASTObjectToBytecodeCompilationStage,
    ASTObjectToJSONBytecodeCompilationStage,
    ASTObjectToLEDSourceCodeCompilationStage,
    ASTOptimisationStage,
    BytecodeToASTObjectCompilationStage,
    CompilationStageExecutionEnvironment,
    JSONBytecodeToASTObjectCompilationStage,
    LEDSourceCodeToASTObjectCompilationStage,
)


class BytecodeCompiler:
    """Bytecode compiler that produces raw bytecode from input files in
    various formats.
    """

    def __init__(
        self,
        *,
        optimisation_level: int = 0,
        progress: bool = False,
        verbose: bool = False
    ):
        """Constructor.

        Parameters:
            optimisation_level: the optimisation level that the compiler
                will use. Defaults to not optimising the bytecode at all.
            progress: whether to print a progress bar showing the
                progress of the compilation
            verbose: whether to print additional messages about the compilation
                process above the progress bar
        """
        self._optimisation_level = 0

        self._input_format_to_ast_stage_factory = {
            InputFormat.LEDCTRL_BINARY: BytecodeToASTObjectCompilationStage,
            InputFormat.LEDCTRL_SOURCE: LEDSourceCodeToASTObjectCompilationStage,
            InputFormat.LEDCTRL_JSON: JSONBytecodeToASTObjectCompilationStage,
        }
        self._output_format_to_output_stage_factory = {
            OutputFormat.LEDCTRL_BINARY: ASTObjectToBytecodeCompilationStage,
            OutputFormat.LEDCTRL_SOURCE: ASTObjectToLEDSourceCodeCompilationStage,
            OutputFormat.LEDCTRL_JSON: ASTObjectToJSONBytecodeCompilationStage,
        }

        self.optimisation_level = int(optimisation_level)
        self.progress = progress
        self.verbose = verbose

        self.environment = CompilationStageExecutionEnvironment(self)
        self.output = None

    def compile(
        self,
        input: Any,
        output_file: Optional[str] = None,
        *,
        input_format: Optional[InputFormatLike] = None,
        output_format: Optional[OutputFormatLike] = None
    ) -> Tuple[Any]:
        """Runs the compiler.

        Parameters:
            input: the input to compile. When it is a string or a Path object, it is
                assumed to be the name of a file that contains the input. When it is
                a bytes object, it is assumed to contain the raw data to compile;
                in this case, the ``input_format`` parameter must be specified.
                When it is a dictionary, it is assumed to be the Python
                representation of a JSON object and the ``input_format`` will
                be assumed to be ``InputFormat.LEDCTRL_JSON``.
            output_file: the name of the output file that the compiler will
                produce. When the compiler is expected to produce multiple
                output objects, the output file is expected to contain a
                ``{}`` placeholder where the index of the output object will be
                substituted. The output file may also be ``None`` if the
                compiler should only return the output
            input_format: the preferred input format or ``None`` if it should
                be inferred from the extension of the input file
            output_format: the preferred output format or ``None`` if it should
                be inferred from the extension of the output file

        Returns:
            a tuple containing all the objects that the compiler returned.
            Typically the tuple will contain a single item only (if the
            compilation yields a single output).

        Raises:
            CompilerError: in case of a compilation error
        """
        if isinstance(input, Path):
            input = str(input)

        if isinstance(input, str):
            if input_format is None:
                input_format = InputFormat.detect_from_filename(input)

            description = os.path.basename(input)
            with open(input, "rb") as fp:
                input = fp.read()

        elif isinstance(input, bytes):
            description = "<<raw bytes>>"

        elif isinstance(input, dict):
            from json import dumps

            description = "<<JSON>>"
            input = dumps(input).encode("utf-8")
            input_format = InputFormat.LEDCTRL_JSON

        if input_format is None:
            raise CompilerError("input format must be specified")

        if output_format is None:
            if output_file is not None:
                output_format = OutputFormat.detect_from_filename(output_file)
            else:
                output_format = OutputFormat.AST

        input_format = InputFormat(input_format)
        output_format = OutputFormat(output_format)

        plan = Plan()
        self._collect_stages(plan, input, input_format, output_format)
        self.output = plan.execute(
            self.environment,
            force=True,
            progress=self.progress,
            description=description,
            verbose=self.verbose,
        )
        if output_file:
            self._write_outputs_to_file(self.output, output_file)

        return self.output

    @property
    def optimisation_level(self):
        """The optimisation level that the compiler will use.

        Currently we have the following optimisation levels:

            - 0: don't optimise the AST at all

            - 1: perform only basic optimisations

            - 2: perform more aggressive optimisations to make the generated
            bytecode smaller (default)
        """
        return self._optimisation_level

    @optimisation_level.setter
    def optimisation_level(self, value):
        self._optimisation_level = max(0, int(value))

    def _collect_stages(
        self,
        plan: Plan,
        input_data: bytes,
        input_format: InputFormat,
        output_format: OutputFormat,
    ):
        """Collects the compilation stages that will turn the given input
        file into the given output file.

        Parameters:
            plan: compilation plan where the collected stages will be added to
            input_data: the input data to work on
            input_format: the format of the input data
            output_format: the preferred output format

        Raises:
            UnsupportedInputFormatError: when the format of the input file is
                not known to the compiler
        """
        # Add the stages required to produce an abstract syntax tree
        # representation of the LED program based on the extension of the
        # input file
        create_ast_stage = self._input_format_to_ast_stage_factory.get(input_format)
        if create_ast_stage is None:
            raise UnsupportedInputFormatError(format=input_format)

        ast_stage = create_ast_stage(input_data)
        plan.add_step(ast_stage)

        # Create a list containing our only AST stage; this may be useful later
        # when one input file may produce multiple ASTs
        ast_stages = [ast_stage]

        # Create a function that adds an optimization stage for the AST stage
        # given as an input
        def create_optimisation_stage(ast_stage):
            optimiser = create_optimiser_for_level(self.optimisation_level)
            return ASTOptimisationStage(ast_stage, optimiser)

        # Determine which factory to use for the output stages
        create_output_stage = self._output_format_to_output_stage_factory.get(
            output_format
        )

        # Create the optimization stages and the output stages for each AST
        for index, ast_stage in enumerate(ast_stages):
            optimisation_stage = create_optimisation_stage(ast_stage)
            plan.add_step(optimisation_stage)

            if create_output_stage:
                output_stage = create_output_stage(optimisation_stage)
                plan.add_step(output_stage)
            else:
                output_stage = optimisation_stage

            plan.mark_as_output(output_stage)

    def _write_outputs_to_file(self, outputs, output_file):
        if not outputs:
            return

        if len(outputs) > 1 and "{}" not in output_file:
            raise CompilerError(
                "output filename needs to include a {} placeholder if the "
                "compiler produces multiple outputs"
            )

        num_digits = len(str(len(outputs) - 1))
        id_format = "{0:0" + str(num_digits) + "}"

        for index, output in enumerate(outputs):
            id = id_format.format(index)
            with open(output_file.format(id), "wb") as fp:
                fp.write(output)

    """
    def _add_stages_for_input_sce_file(self, input_file, output_file, plan):
        if "{}" not in output_file:
            raise CompilerError(
                "output file needs to include a {} placeholder for the "
                "FX identifier when compiling a Sunlite Suite scene "
                "file"
            )
        led_file_template = self._create_intermediate_filename(output_file, ".led")

        parsing_stage = SunliteSceneParsingStage(input_file)
        plan.add_step(parsing_stage)

        @plan.when_step_is_done(parsing_stage)
        def create_next_stages(output):
            preproc_stage = ParsedSunliteScenesToPythonSourceCompilationStage(
                [(0, None, output)], led_file_template, start_at=0
            )
            plan.add_step(preproc_stage)

            intermediate_files = preproc_stage.output_files_by_ids.items()
            for id, intermediate_file in intermediate_files:
                stage = LEDSourceCodeToASTObjectCompilationStage(
                    intermediate_file, id=id
                )
                plan.add_step(stage)

        return parsing_stage

    def _add_stages_for_input_ses_file(self, input_file, output_file, plan):
        # Get the directory in which the input .ses file is contained --
        # we will assume that all the .sce files that the .ses file refers to
        # are in the same directory
        dirname = os.path.dirname(input_file)

        # Create filename templates for the LED files
        if "{}" not in output_file:
            raise CompilerError(
                "output file needs to include a {} placeholder for the "
                "FX identifier when compiling a Sunlite Suite scene "
                "file"
            )
        led_file_template = self._create_intermediate_filename(output_file, ".led")

        # Parse the .ses file, and find all the .sce files that we depend on
        ses_parsing_stage = SunliteSwitchParsingStage(input_file)
        plan.add_step(ses_parsing_stage)

        # Create a dummy stage that will be reached when we have added all
        # the steps in the plan that eventually yields an AST (abstract
        # syntax tree)
        marker_stage = DummyStage()
        plan.add_step(marker_stage)
        add_step = partial(plan.insert_step, before=marker_stage)

        # Define the "continuation function" for the stage that parses the
        # .ses file. The continuation is responsible for parsing each
        # .sce file that the .ses file depends on
        @plan.when_step_is_done(ses_parsing_stage)
        def parse_scene_files(parsed_ses_file):
            sce_dependencies = dict(
                (file_id, os.path.join(dirname, filename) + ".sce")
                for file_id, filename in parsed_ses_file.files.iteritems()
            )

            # Add steps to parse each .sce file into an in-memory object.
            # At the end of each such step, store the result back into
            # sce_dependencies
            def store_parsed_scene_file(id, parsed_sce_file):
                sce_dependencies[id] = parsed_sce_file

            sce_parsing_stages = []
            for sce_file_id in list(sce_dependencies.keys()):
                filename = sce_dependencies[sce_file_id]
                sce_parsing_stage = SunliteSceneParsingStage(filename)
                sce_parsing_stages.append(sce_parsing_stage)
                add_step(sce_parsing_stage).and_when_done(
                    partial(store_parsed_scene_file, sce_file_id)
                )

            # When the last .sce file has been parsed, we need to
            # calculate the final scene ordering and then add steps
            # to convert the .sce files into the abstract syntax tree
            # (AST) representation
            last_sce_parsing_stage = sce_parsing_stages[-1]
            if not last_sce_parsing_stage:
                return

            @plan.when_step_is_done(last_sce_parsing_stage)
            def convert_scene_files_to_ast(output):
                # Calculate the final scene ordering
                scene_order = [
                    (btn.position, btn.size, sce_dependencies[btn.name])
                    for btn in parsed_ses_file.buttons
                ]

                # Add the preprocessing stage that merges multiple Sunlite
                # Suite scene files into .led (Python) source files, sorted
                # by FX IDs
                preproc_stage = ParsedSunliteScenesToPythonSourceCompilationStage(
                    scene_order, led_file_template, start_at=0
                )
                add_step(preproc_stage)

                # For each intermediate .led (Python) file created in the
                # preprocessing stage, add a stage to compile the
                # corresponding .ast file
                intermediate_files = preproc_stage.output_files_by_ids.items()
                for id, intermediate_file in intermediate_files:
                    stage = LEDSourceCodeToASTObjectCompilationStage(
                        intermediate_file, id=id
                    )
                    add_step(stage, output)

        return marker_stage

    def _create_intermediate_filename(self, output_file, ext):
        \"""Creates an intermediate filename or filename template from the
        given output filename by replacing its extension with another one.

        :param output_file: the name of the output file as asked by the user
        :type output_file: str
        :param ext: the desired extension of the intermediate file
        :type ext: str
        :return: the name of the intermediate file
        :rtype: str
        \"""
        base, orig_ext = os.path.splitext(output_file)
        if orig_ext == ext:
            raise ValueError(
                "cannot create an intermediate file with "
                "extension {0!r} because the name of the output "
                "file has the same extension".format(orig_ext)
            )
        if self._tmpdir:
            base = os.path.basename(base)
            return os.path.join(self._tmpdir, base + ext)
        else:
            return base + ext
    """


def compile(
    input: Any,
    output_file: Optional[str] = None,
    *,
    input_format: Optional[InputFormatLike] = None,
    output_format: Optional[OutputFormatLike] = None,
    **kwds
):
    """Runs the compiler.

    This function is a syntactic sugar for one-time throwaway compilations.
    For more sophisticated use-cases, use the BytecodeCompiler_ class.

    Keyword arguments not mentioned here are forwarded to the BytecodeCompiler_
    constructor.

    Parameters:
        input: the input to compile. When it is a string, it is assumed to
            be the name of a file that contains the input. When it is a
            bytes object, it is assumed to contain the raw data to compile;
            in this case, the ``input_format`` parameter must be specified.
            When it is a dictionary, it is assumed to be the Python
            representation of a JSON object and the ``input_format`` will
            be assumed to be ``InputFormat.LEDCTRL_JSON``.
        output_file: the name of the output file that the compiler will
            produce. When the compiler is expected to produce multiple
            output objects, the output file is expected to contain a
            ``{}`` placeholder where the index of the output object will be
            substituted. The output file may also be ``None`` if the
            compiler should only return the output
        input_format: the preferred input format or ``None`` if it should
            be inferred from the extension of the input file
        output_format: the preferred output format or ``None`` if it should
            be inferred from the extension of the output file

    Returns:
        None if the compiler returned nothing; the result of the compilation if
        the compiler returned a single object only, or a tuple containing the
        result of the compilation if the compiler returned multiple objects

    Raises:
        CompilerError: in case of a compilation error
    """
    compiler = BytecodeCompiler(**kwds)
    result = compiler.compile(
        input, output_file, input_format=input_format, output_format=output_format
    )

    if not result:
        return None

    if len(result) == 1:
        return result[0]

    return result
