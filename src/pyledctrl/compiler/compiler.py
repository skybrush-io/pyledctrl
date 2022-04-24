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
