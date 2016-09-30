"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats."""

import os

from pyledctrl.compiler.errors import CompilerError, \
    UnsupportedInputFileFormatError
from pyledctrl.compiler.plan import Plan
from pyledctrl.compiler.stages import \
    ParsedSunliteScenesToPythonSourceCompilationStage, \
    PythonSourceToASTObjectCompilationStage, \
    SunliteSceneParsingStage, \
    SunliteSwitchParsingStage, \
    ASTObjectToBytecodeCompilationStage, \
    ASTObjectToLEDFileCompilationStage, \
    ASTObjectToProgmemHeaderCompilationStage
from pyledctrl.utils import TemporaryDirectory


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
    various formats."""

    def __init__(self, keep_intermediate_files=False):
        self.keep_intermediate_files = keep_intermediate_files
        self._tmpdir = None

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

    def _compile(self, input_file, output_file, force):
        plan = Plan()
        self._collect_stages(input_file, output_file, plan)
        self.output = plan.execute(force=force)

    def _collect_stages(self, input_file, output_file, plan):
        """Collects the compilation stages that will turn the given input
        file into the given output file.

        :param input_file: the name of the input file
        :type input_file: str
        :param output_file: the name of the output file or ``None`` if we only
            need to generate an abstract syntax tree
        :type output_file: str or None
        :param plan: compilation plan where the collected stages will be added to
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

        # Add the stages required to produce an abstract syntax tree
        # representation of the LED program based on the extension of the
        # input file
        if ext == ".led":
            self._add_stages_for_input_led_file(input_file, output_file, plan,
                                                ast_only)
        elif ext == ".sce":
            self._add_stages_for_input_sce_file(input_file, output_file, plan,
                                                ast_only)
        elif ext == ".ses":
            self._add_stages_for_input_ses_file(input_file, output_file, plan,
                                                ast_only)
        else:
            raise UnsupportedInputFileFormatError(ext)

        # At this point the input has been converted into an abstract syntax
        # tree (AST). It's time to add an optimization stage.

        # Add the stages based on the extension of the output file
        if output_ext is None:
            output_stage_factory = None
        elif output_ext == ".h":
            output_stage_factory = ASTObjectToProgmemHeaderCompilationStage
        elif output_ext == ".oled":
            output_stage_factory = ASTObjectToLEDFileCompilationStage
        else:
            output_stage_factory = ASTObjectToBytecodeCompilationStage

        # We need to generate an output file for each AST object.
        for stage in plan.iter_steps(PythonSourceToASTObjectCompilationStage):
            if getattr(stage, "id", None) is not None:
                real_output_file = output_file.replace("{}", stage.id)
            else:
                real_output_file = output_file
            new_stage = output_stage_factory(stage, real_output_file)
            plan.insert_step(new_stage, after=stage)

    def _add_stages_for_input_led_file(self, input_file, output_file, plan,
                                       ast_only):
        stage = PythonSourceToASTObjectCompilationStage(input_file)
        plan.add_step(stage, output=ast_only)

    def _add_stages_for_input_sce_file(self, input_file, output_file, plan,
                                       ast_only):
        parsing_stage = SunliteSceneParsingStage(input_file)
        parsing_stage.run()

        if ast_only:
            led_file_template = self._create_intermediate_filename(
                "stage{}_" + input_file, ".led"
            )
        else:
            if "{}" not in output_file:
                raise CompilerError("output file needs to include {} placeholder "
                                    "for the FX id when compiling a Sunlite "
                                    "Suite scene file")
            led_file_template = self._create_intermediate_filename(output_file, ".led")

        preprocessing_stage = ParsedSunliteScenesToPythonSourceCompilationStage(
            [(0, None, parsing_stage.output)], led_file_template
        )
        plan.add_step(preprocessing_stage)

        for id, intermediate_file in preprocessing_stage.output_files_by_ids.items():
            stage = PythonSourceToASTObjectCompilationStage(intermediate_file)
            plan.add_step(stage, output=ast_only)

    def _add_stages_for_input_ses_file(self, input_file, output_file, plan,
                                       ast_only):
        # Get the directory in which the input .ses file is contained --
        # we will assume that all the .sce files that the .ses file refers to
        # are in the same directory
        dirname = os.path.dirname(input_file)

        # Parse the .ses file, and find all the .sce files that we depend on
        ses_parsing_stage = SunliteSwitchParsingStage(input_file)
        ses_parsing_stage.run()
        parsed_ses_file = ses_parsing_stage.output
        sce_dependencies = dict(
            (file_id, os.path.join(dirname, filename) + ".sce")
            for file_id, filename in parsed_ses_file.files.iteritems()
        )

        # Parse each .sce file into an in-memory object
        for sce_file_id in list(sce_dependencies.keys()):
            filename = sce_dependencies[sce_file_id]
            sce_parsing_stage = SunliteSceneParsingStage(filename)
            sce_parsing_stage.run()
            sce_dependencies[sce_file_id] = sce_parsing_stage.output

        # Calculate the final scene ordering
        scene_order = [
            (button.position, button.size, sce_dependencies[button.name])
            for button in parsed_ses_file.buttons
        ]

        # Create filename templates for the LED files
        if ast_only:
            led_file_template = self._create_intermediate_filename(
                "stage{}_" + input_file, ".led"
            )
        else:
            if "{}" not in output_file:
                raise CompilerError("output file needs to include {} placeholder "
                                    "for the FX id when compiling a Sunlite "
                                    "Suite scene file")
            led_file_template = self._create_intermediate_filename(output_file, ".led")

        # Add the preprocessing stage that merges multiple Sunlite Suite scene
        # files into .led (Python) source files, sorted by FX IDs
        preprocessing_stage = ParsedSunliteScenesToPythonSourceCompilationStage(
            scene_order, led_file_template
        )
        plan.add_step(preprocessing_stage)

        # For each intermediate .led (Python) file created in the preprocessing
        # stage, add a stage to compile the corresponding .ast file
        for id, intermediate_file in preprocessing_stage.output_files_by_ids.items():
            stage = PythonSourceToASTObjectCompilationStage(intermediate_file,
                                                            id=id)
            plan.add_step(stage, output=ast_only)

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
            raise ValueError("cannot create an intermediate file with "
                             "extension {0!r} because the name of the output "
                             "file has the same extension".format(orig_ext))
        if self._tmpdir:
            base = os.path.basename(base)
            return os.path.join(self._tmpdir, base + ext)
        else:
            return base + ext
