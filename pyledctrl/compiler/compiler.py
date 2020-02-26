"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats.
"""

import os

from functools import partial
from typing import Optional

from pyledctrl.utils import TemporaryDirectory

from .errors import CompilerError, UnsupportedInputFormatError
from .formats import InputFormat, OutputFormat
from .optimisation import create_optimiser_for_level
from .plan import Plan
from .stages import (
    ASTObjectToBytecodeCompilationStage,
    ASTObjectToJSONBytecodeCompilationStage,
    ASTObjectToLEDFileCompilationStage,
    ASTOptimisationStage,
    BytecodeToASTObjectCompilationStage,
    CompilationStageExecutionEnvironment,
    DummyStage,
    FileToASTObjectCompilationStage,
    ParsedSunliteScenesToPythonSourceCompilationStage,
    PythonSourceToASTObjectCompilationStage,
    SunliteSceneParsingStage,
    SunliteSwitchParsingStage,
)


def _replace_extension(filename: str, ext: str) -> str:
    """Replaces the extension of the given filename with another one.

    Parameters:
        filename: the filename to modify
        ext: the desired extension of the file

    Returns:
        the new filename
    """
    base, _ = os.path.splitext(filename)
    return base + ext


class BytecodeCompiler:
    """Bytecode compiler that produces raw bytecode from input files in
    various formats.
    """

    def __init__(
        self,
        *,
        optimisation_level: int = 2,
        keep_intermediate_files: bool = False,
        progress: bool = False,
        verbose: bool = False
    ):
        """Constructor.

        Parameters:
            optimisation_level: the optimisation level that the compiler
                will use. Defaults to optimising for the smallest bytecode.
            keep_intermediate_files: whether to keep any intermediate
                files that are created during compilation
            progress: whether to print a progress bar showing the
                progress of the compilation
            verbose: whether to print additional messages about the compilation
                process above the progress bar
        """
        self._tmpdir = None
        self._optimiser = None
        self._optimisation_level = 0

        self._input_format_to_ast_stage_factory = {
            InputFormat.LEDCTRL_BINARY: self._add_stages_for_input_bin_file,
            InputFormat.LEDCTRL_SOURCE: self._add_stages_for_input_led_file,
            InputFormat.SUNLITE_STUDIO_SCE: self._add_stages_for_input_sce_file,
            InputFormat.SUNLITE_STUDIO_SES: self._add_stages_for_input_ses_file,
        }
        self._output_format_to_output_stage_factory = {
            OutputFormat.LEDCTRL_BINARY: ASTObjectToBytecodeCompilationStage,
            OutputFormat.LEDCTRL_SOURCE: ASTObjectToLEDFileCompilationStage,
            OutputFormat.LEDCTRL_JSON: ASTObjectToJSONBytecodeCompilationStage,
        }

        self.keep_intermediate_files = keep_intermediate_files
        self.optimisation_level = int(optimisation_level)
        self.progress = progress
        self.shift_by = 0
        self.verbose = verbose

        self.environment = CompilationStageExecutionEnvironment(self)

    def compile(self, input_file, output_file=None, force=True):
        """Runs the compiler.

        Parameters:
            input_file (str): the input file to compile
            output_file (Optional[str]): the output file that the compiler will
                produce or ``None`` if we only need the abstract syntax tree
                representation of the input
            force (bool): force compilation even if the input file is older
                than the output file. Ignored if ``output_file`` is ``None``

        Raises:
            CompilerError: in case of a compilation error
        """
        if self.keep_intermediate_files:
            return self._compile(input_file, output_file, force)
        else:
            with TemporaryDirectory() as tmpdir:
                self._tmpdir = tmpdir
                result = self._compile(input_file, output_file, force)
                self._tmpdir = None
            return result

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
        if self._optimisation_level == value:
            return

        self._optimisation_level = value
        self._optimiser = create_optimiser_for_level(value)

    def _compile(self, input_file, output_file, force):
        description = os.path.basename(input_file) if input_file is not None else None

        plan = Plan()
        self._collect_stages(input_file, output_file, plan)
        self.output = plan.execute(
            self.environment,
            force=force,
            progress=self.progress,
            description=description,
            verbose=self.verbose,
        )

    def _collect_stages(self, input_file: str, output_file: Optional[str], plan: Plan):
        """Collects the compilation stages that will turn the given input
        file into the given output file.

        Parameters:
            input_file: the name of the input file
            output_file: the name of the output file or ``None`` if we only
                need to generate an abstract syntax tree
            plan: compilation plan where the collected stages will be added to

        Raises:
            UnsupportedInputFormatError: when the format of the input file is
                not known to the compiler
        """
        input_format = InputFormat.detect_from_filename(input_file)

        if output_file is not None:
            output_format = OutputFormat.detect_from_filename(output_file)
        else:
            output_format = OutputFormat.AST

        # Shifting is supported for ``.sce`` and ``.ses`` only
        if (
            input_format
            not in (InputFormat.SUNLITE_STUDIO_SCE, InputFormat.SUNLITE_STUDIO_SES)
            and self.shift_by != 0
        ):
            raise CompilerError("Shifting is supported only for Sunlite Suite files")

        # Add the stages required to produce an abstract syntax tree
        # representation of the LED program based on the extension of the
        # input file
        create_ast_stage = self._input_format_to_ast_stage_factory.get(input_format)
        if create_ast_stage is None:
            raise UnsupportedInputFormatError(format=input_format)
        ast_stage = create_ast_stage(
            input_file, output_file, plan, ast_only=output_format is OutputFormat.AST
        )

        # Determine the final optimization level to use
        # TODO(ntamas): if the output is ".led", don't optimize; otherwise
        # respect the setting of the user
        # TODO(ntamas): when forced not to optimize, set create_optimisation_stage
        # to None
        def create_optimisation_stage(ast_stage):
            return ASTOptimisationStage(ast_stage, self._optimiser)

        # Determine which factory to use for the output stages
        create_output_stage = self._output_format_to_output_stage_factory.get(
            output_format
        )

        # When the execution of the AST step is done, we need to generate
        # an output file for each AST object. We cannot do this in advance
        # because it may happen that there are already some callbacks
        # registered on the AST step that create new steps in the plan.
        @plan.when_step_is_done(ast_stage)
        def generate_output_files(output=None):
            # We need to generate an output file for each AST object.
            for stage in plan.iter_steps(FileToASTObjectCompilationStage):
                if getattr(stage, "id", None) is not None:
                    real_output_file = output_file.replace("{}", stage.id)
                else:
                    real_output_file = output_file

                if create_optimisation_stage:
                    optimization_stage = create_optimisation_stage(stage)
                    plan.add_step(optimization_stage)

                if create_output_stage:
                    output_stage = create_output_stage(
                        optimization_stage, real_output_file, id=stage.id
                    )
                    plan.add_step(output_stage)

    def _add_stages_for_input_bin_file(self, input_file, output_file, plan, ast_only):
        stage = BytecodeToASTObjectCompilationStage(input_file)
        plan.add_step(stage, output=ast_only)
        return stage

    def _add_stages_for_input_led_file(self, input_file, output_file, plan, ast_only):
        stage = PythonSourceToASTObjectCompilationStage(input_file)
        plan.add_step(stage, output=ast_only)
        return stage

    def _add_stages_for_input_sce_file(self, input_file, output_file, plan, ast_only):
        if ast_only:
            led_file_template = self._create_intermediate_filename(
                "stage{}_" + input_file, ".led"
            )
        else:
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
                [(0, None, output)], led_file_template, start_at=self.shift_by
            )
            plan.add_step(preproc_stage)

            intermediate_files = preproc_stage.output_files_by_ids.items()
            for id, intermediate_file in intermediate_files:
                stage = PythonSourceToASTObjectCompilationStage(
                    intermediate_file, id=id
                )
                plan.add_step(stage, output=ast_only)

        return parsing_stage

    def _add_stages_for_input_ses_file(self, input_file, output_file, plan, ast_only):
        # Get the directory in which the input .ses file is contained --
        # we will assume that all the .sce files that the .ses file refers to
        # are in the same directory
        dirname = os.path.dirname(input_file)

        # Create filename templates for the LED files
        if ast_only:
            led_file_template = self._create_intermediate_filename(
                "stage{}_" + input_file, ".led"
            )
        else:
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
                    scene_order, led_file_template, start_at=self.shift_by
                )
                add_step(preproc_stage)

                # For each intermediate .led (Python) file created in the
                # preprocessing stage, add a stage to compile the
                # corresponding .ast file
                intermediate_files = preproc_stage.output_files_by_ids.items()
                for id, intermediate_file in intermediate_files:
                    stage = PythonSourceToASTObjectCompilationStage(
                        intermediate_file, id=id
                    )
                    add_step(stage, output=ast_only)

        return marker_stage

    def _create_intermediate_filename(self, output_file, ext):
        """Creates an intermediate filename or filename template from the
        given output filename by replacing its extension with another one.

        :param output_file: the name of the output file as asked by the user
        :type output_file: str
        :param ext: the desired extension of the intermediate file
        :type ext: str
        :return: the name of the intermediate file
        :rtype: str
        """
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
