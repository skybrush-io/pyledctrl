"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats."""

import os

from pyledctrl.compiler.errors import CompilerError, \
    UnsupportedInputFileFormatError
from pyledctrl.compiler.plan import Plan
from pyledctrl.compiler.stages import \
    SunliteSceneToPythonSourceCompilationStage, \
    PythonSourceToASTFileCompilationStage, ASTFileToBytecodeCompilationStage, \
    ASTFileToProgmemHeaderCompilationStage
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

    def compile(self, input_file, output_file, force=True):
        """Runs the compiler.

        :param input_file: the input file to compiler
        :type input_file: str
        :param output_file: the output file that the compiler will produce
        :type output_file: str
        :param force: force compilation even if the input file is older than
           the output file
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
        plan.execute(force=force)

    def _collect_stages(self, input_file, output_file, plan):
        """Collects the compilation stages that will turn the given input
        file into the given output file.

        :param input_file: the name of the input file
        :type input_file: str
        :param output_file: the name of the output file
        :type output_file: str
        :param plan: compilation plan where the collected stages will be added to
        :type plan: Plan

        :raises UnsupportedInputFileFormatError: when the format of the input
            file is not known to the compiler
        """
        _, ext = os.path.splitext(input_file)
        ext = ext.lower()

        _, output_ext = os.path.splitext(output_file)
        output_ext = output_ext.lower()

        # Add the stages required to produce an abstract syntax tree
        # representation of the LED program based on the extension of the
        # input file
        if ext == ".led":
            ast_file = self._create_intermediate_filename(output_file, ".ast")
            plan.add_step(
                PythonSourceToASTFileCompilationStage(input_file, ast_file)
            )
        elif ext == ".sce":
            if "{}" not in output_file:
                raise CompilerError("output file needs to include {} placeholder "
                                    "for the FX id when compiling a Sunlite "
                                    "Suite scene file")
            ast_file_template = self._create_intermediate_filename(output_file, ".ast")
            led_file_template = self._create_intermediate_filename(output_file, ".led")
            preprocessing_stage = SunliteSceneToPythonSourceCompilationStage(
                input_file, led_file_template)
            plan.add_step(preprocessing_stage)
            for id, intermediate_file in preprocessing_stage.output_files_by_ids.items():
                stage = PythonSourceToASTFileCompilationStage(
                    intermediate_file,
                    ast_file_template.replace("{}", id),
                    id=id
                )
                plan.add_step(stage)
        else:
            raise UnsupportedInputFileFormatError(ext)

        # Add the stages based on the extension of the output file
        if output_ext == ".h":
            output_stage_factory = ASTFileToProgmemHeaderCompilationStage
        else:
            output_stage_factory = ASTFileToBytecodeCompilationStage

        # We need to generate an output file for each AST file.
        for stage in plan.iter_steps(PythonSourceToASTFileCompilationStage):
            if stage.id is not None:
                real_output_file = output_file.replace("{}", stage.id)
            else:
                real_output_file = output_file
            new_stage = output_stage_factory(stage.output, real_output_file)
            plan.insert_step(new_stage, after=stage)

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
