"""Module that implements the bytecode compiler that produces raw bytecode
from input files in various formats."""

import os

from .errors import CompilerError, UnsupportedInputFileFormatError
from .stages import SunliteSceneToPythonSourceCompilationStage, \
    PythonSourceToBytecodeCompilationStage, \
    BytecodeToProgmemHeaderCompilationStage


class BytecodeCompiler(object):
    """Bytecode compiler that produces raw bytecode from input files in
    various formats."""

    def __init__(self):
        pass

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
        plan = []
        self._collect_stages(input_file, output_file, plan)
        last_step = plan[-1] if plan else None

        for step in plan:
            if force or step == last_step or step.should_run():
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

        _, output_ext = os.path.splitext(output_file)
        output_ext = output_ext.lower()

        # Add the stages based on the extension of the input file
        if ext == ".led":
            plan.append(PythonSourceToBytecodeCompilationStage(input_file, output_file))
        elif ext == ".sce":
            if "{}" not in output_file:
                raise CompilerError("output file needs to include {} placeholder "
                                    "for the FX id when compiling a Sunlite "
                                    "Suite scene file")
            preprocessing_stage = SunliteSceneToPythonSourceCompilationStage(input_file)
            plan.append(preprocessing_stage)
            for id, intermediate_file in preprocessing_stage.output_files_by_ids.items():
                stage = PythonSourceToBytecodeCompilationStage(
                    intermediate_file,
                    output_file.replace("{}", id)
                )
                plan.append(stage)
        else:
            raise UnsupportedInputFileFormatError(ext)

        # Add the stages based on the extension of the output file
        if output_ext == ".h":
            # We need to generate a PROGMEM header file for each bytecode file
            for index, stage in reversed(list(enumerate(plan))):
                if isinstance(stage, PythonSourceToBytecodeCompilationStage):
                    output_file = stage.output
                    stage.output = output_file.replace(".h", ".bin")
                    new_stage = BytecodeToProgmemHeaderCompilationStage(
                        stage.output, output_file)
                    plan.insert(index+1, new_stage)
        else:
            # We are okay with the stages that we have now
            return
