"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats.
"""

import logging
import os

from functools import partial

from pyledctrl.compiler.errors import CompilerError, UnsupportedInputFileFormatError
from pyledctrl.compiler.optimisation import create_optimiser_for_level
from pyledctrl.compiler.plan import Plan
from pyledctrl.compiler.stages import (
    DummyStage,
    CompilationStageExecutionEnvironment,
    ParsedSunliteScenesToPythonSourceCompilationStage,
    PythonSourceToASTObjectCompilationStage,
    SunliteSceneParsingStage,
    SunliteSwitchParsingStage,
    ASTObjectToBytecodeCompilationStage,
    ASTObjectToLEDFileCompilationStage,
    ASTObjectToProgmemHeaderCompilationStage,
    ASTOptimisationStage,
)
from pyledctrl.utils import TemporaryDirectory

log = logging.getLogger("pyledctrl.compiler.compiler")


def _replace_extension(filename, ext):
    """Replaces the extension of the given filename with another one.

    :param filename: the filename to modify
    :type filename: str
    :param ext: the desired extension of the file
    :type ext: str
    :return: the new filename
    :rtype: str
    """
    base, _ = os.path.splitext(filename)
    return base + ext


class BytecodeCompiler(object):
    """Bytecode compiler that produces raw bytecode from input files in
    various formats.
    """

    def __init__(self, keep_intermediate_files=False, verbose=False):
        """Constructor.

        Parameters:
            keep_intermediate_files (bool): whether to keep any intermediate
                files that are created during compilation
            verbose (bool): whether to print messages about the progress of
                the compilation
        """
        self.keep_intermediate_files = keep_intermediate_files
        self._tmpdir = None
        self._optimiser = None
        self._optimisation_level = 0
        self.optimisation_level = 2
        self.shift_by = 0
        self.verbose = verbose
        self.environment = CompilationStageExecutionEnvironment(self)

    def compile(self, input_file, output_file=None, force=True):
        """Runs the compiler.

        :param input_file: the input file to compiler
        :type input_file: str
        :param output_file: the output file that the compiler will produce or
            ``None`` if we only need the abstract syntax tree representation
            of the input
        :type output_file: str or None
        :param force: force compilation even if the input file is older than
           the output file. Ignored if ``output_file`` is ``None``.
        :type force: bool

        :raises CompilerError: in case of a compilation error
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
        plan = Plan()
        self._collect_stages(input_file, output_file, plan)
        self.output = plan.execute(self.environment, force=force, verbose=self.verbose)

    def _collect_stages(self, input_file, output_file, plan):
        """Collects the compilation stages that will turn the given input
        file into the given output file.

        :param input_file: the name of the input file
        :type input_file: str
        :param output_file: the name of the output file or ``None`` if we only
            need to generate an abstract syntax tree
        :type output_file: str or None
        :param plan: compilation plan where the collected stages will be
            added to
        :type plan: Plan

        :return: list of stages that generate their outputs in memory and that
            should be collected in the ``output`` property of the compiler at
            the end of the compilation
        :rtype: list of CompilationStage

        :raises UnsupportedInputFileFormatError: when the format of the input
            file is not known to the compiler
        """
        _, ext = os.path.splitext(input_file)
        ext = ext.lower()

        if output_file is not None:
            _, output_ext = os.path.splitext(output_file)
            output_ext = output_ext.lower()
            ast_only = False
        else:
            output_ext = None
            ast_only = True

        # Shifting is supported for ``.sce`` and ``.ses`` only
        if ext not in (".sce", ".ses") and self.shift_by != 0:
            raise CompilerError("Shifting is supported only for Sunlite " "Suite files")

        # Add the stages required to produce an abstract syntax tree
        # representation of the LED program based on the extension of the
        # input file
        if ext == ".led" or ext == ".oled":
            func = self._add_stages_for_input_led_file
        elif ext == ".sce":
            func = self._add_stages_for_input_sce_file
        elif ext == ".ses":
            func = self._add_stages_for_input_ses_file
        else:
            raise UnsupportedInputFileFormatError(ext)
        ast_step = func(input_file, output_file, plan, ast_only)

        # Determine which factory to use for the output stages
        if output_ext is None:
            output_stage_factory = None
        elif output_ext == ".h":
            output_stage_factory = ASTObjectToProgmemHeaderCompilationStage
        elif output_ext == ".oled":
            output_stage_factory = ASTObjectToLEDFileCompilationStage
        else:
            output_stage_factory = ASTObjectToBytecodeCompilationStage

        # When the execution of the AST step is done, we need to generate
        # an output file for each AST object. We cannot do this in advance
        # because it may happen that there are already some callbacks
        # registered on the AST step that create new steps in the plan.
        @plan.when_step_is_done(ast_step)
        def generate_output_files(output=None):
            # We need to generate an output file for each AST object.
            ast_stage_class = PythonSourceToASTObjectCompilationStage
            for stage in plan.iter_steps(ast_stage_class):
                if getattr(stage, "id", None) is not None:
                    real_output_file = output_file.replace("{}", stage.id)
                else:
                    real_output_file = output_file

                optimization_stage = ASTOptimisationStage(stage, self._optimiser)
                plan.add_step(optimization_stage)

                output_stage = output_stage_factory(
                    optimization_stage, real_output_file, id=stage.id
                )
                plan.add_step(output_stage)

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
