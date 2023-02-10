"""Compilation stages being used in the bytecode compiler."""

import os

from abc import ABC, abstractmethod, abstractproperty
from typing import Generic, List, Optional, TypeVar, Union

from pyledctrl.compiler.optimisation import ASTOptimiser

from .ast import Node
from .contexts import ExecutionContext
from .errors import CompilerError
from .utils import get_timestamp_of

from pyledctrl.logger import log
from pyledctrl.parsers.bytecode import BytecodeParser


S = TypeVar("S")
T = TypeVar("T")


class CompilationStageExecutionEnvironment:
    """Execution environment of compilation stages that contains a few
    functions that the stages may use to access functionality of the
    compiler itself.
    """

    def __init__(self):
        """Constructor."""

    log = log
    warn = log.warn


class CompilationStage(ABC):
    """Compilation stage that can be executed during a course of compilation.

    Stages typically produce a particular kind of output file from one or more
    input files during the compilation. For instance, a compilation stage may
    take a source file with ``.led`` extension, interpret it using a
    compilation context and produce a raw bytecode file with ``.bin``
    extension in the end.
    """

    label = "compiling..."

    @abstractmethod
    def run(self, environment: CompilationStageExecutionEnvironment):
        """Executes the compilation phase.

        Parameters:
            environment: the execution environment of the compilation stage,
                providing useful functions for printing warnings etc
        """
        raise NotImplementedError

    @abstractmethod
    def should_run(self) -> bool:
        """Returns whether the compilation phase should be executed. Returning
        ``False`` typically means that the target of the compilation phase is
        up-to-date so there is no need to re-run the compilation phase.
        """
        raise NotImplementedError


class DummyStage(CompilationStage):
    """Dummy stage that does nothing on its own."""

    def run(self, environment: CompilationStageExecutionEnvironment):
        pass

    def should_run(self) -> bool:
        return True


class FileSourceMixin(ABC):
    """Mixin class for compilation stages that assume that the source of
    the compilation stage is a set of files.
    """

    @abstractproperty
    def input_files(self) -> List[str]:
        """The names of the input files of this compilation stage."""
        raise NotImplementedError

    @property
    def oldest_input_file_timestamp(self) -> float:
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


class FileTargetMixin(ABC):
    """Mixin class for compilation stages that assume that the target of
    the compilation stage is a set of files.
    """

    @abstractproperty
    def output_files(self) -> List[str]:
        """The names of the output files of this compilation stage."""
        raise NotImplementedError

    @property
    def youngest_output_file_timestamp(self) -> float:
        """Returns the timestamp of the youngest output file, positive
        infinity if there are no output files, or negative infinity if at
        least one output file is missing (i.e. does not exist).
        """
        output_files = self.output_files
        if not output_files:
            return float("-inf")
        if any(not os.path.exists(filename) for filename in output_files):
            return float("inf")
        return min(os.path.getmtime(filename) for filename in output_files)


class ObjectSourceMixin(ABC, Generic[S]):
    """Mixin class for compilation stages that assume that the source of
    the compilation stage is an in-memory object.
    """

    @abstractproperty
    def input(self) -> Union[S, "ObjectTargetMixin[S]"]:
        """Returns the input object or the input stage on which this stage
        depends.
        """
        raise NotImplementedError

    @property
    def input_object(self) -> S:
        """Returns the input object on which this stage depends. If the stage
        depends on the output of another stage, this property will return the
        output object of the other stage.
        """
        inp = self.input
        if isinstance(inp, ObjectTargetMixin):
            return inp.output_object  # type: ignore
        else:
            return inp


class ObjectTargetMixin(ABC, Generic[T]):
    """Mixin class for compilation stages that assume that the target of
    the compilation stage is an in-memory object.
    """

    @abstractproperty
    def output(self) -> Union[T, "ObjectTargetMixin[T]"]:
        """THe output object of the compilation stage."""
        raise NotImplementedError

    @property
    def output_object(self) -> T:
        """Returns the output object of this stage. If the output object
        happens to be the same as the input object, and the input
        depends on the output of another stage, this property will return the
        output object of the other stage.
        """
        output = self.output
        if isinstance(output, ObjectTargetMixin):
            return output.output_object  # type: ignore
        else:
            return output


class ConstantOutputStage(DummyStage, ObjectTargetMixin[T]):
    """Dummy output stage that always returns the same object as its output."""

    _output: T

    def __init__(self, output: T):
        super().__init__()
        self._output = output

    @property
    def output(self) -> T:
        """THe output object of the compilation stage."""
        return self._output

    def run(self, environment: CompilationStageExecutionEnvironment):
        pass

    def should_run(self) -> bool:
        return True


class FileToObjectCompilationStage(
    CompilationStage, FileSourceMixin, ObjectTargetMixin[T]
):
    """Abstract compilation phase that turns a set of input files into an
    in-memory object. This phase is executed unconditionally.
    """

    def should_run(self) -> bool:
        """Whether this compilation step should be executed."""
        return True


class ObjectToFileCompilationStage(
    CompilationStage, ObjectSourceMixin[S], FileTargetMixin
):
    """Abstract compilation phase that turns an in-memory object into a set of
    output files. This phase is executed unconditionally if the in-memory
    object is not timestamped (i.e. does not have a ``timestamp`` property);
    otherwise it is executed if the timestamp of the input object is larger
    than the timestamps of any of the output objects.
    """

    def should_run(self) -> bool:
        """Whether this compilation step should be executed.

        The compilation step is executed if the timestamp of the input
        object is later than the timestamp of the youngest output file.
        """
        input_timestamp = get_timestamp_of(
            self.input_object, default_value=float("inf")
        )
        return input_timestamp >= self.youngest_output_file_timestamp


class ObjectToObjectCompilationStage(
    CompilationStage, ObjectSourceMixin[S], ObjectTargetMixin[T]
):
    """Abstract compilation phase that transforms an in-memory object into
    another in-memory object. This phase is executed unconditionally.
    """

    def should_run(self) -> bool:
        """Whether this compilation step should be executed."""
        return True


class FileToFileCompilationStage(CompilationStage, FileSourceMixin, FileTargetMixin):
    """Abstract compilation phase that turns a set of input files into a set
    of output files. The phase is not executed if all the input files are
    older than all the output files.
    """

    def should_run(self) -> bool:
        """Whether this compilation step should be executed.

        The compilation step is executed if the timestamp of the oldest
        input file is not earlier than the timestamp of the youngest
        output file.
        """
        youngest_output = self.youngest_output_file_timestamp
        oldest_input = self.oldest_input_file_timestamp
        return oldest_input >= youngest_output


class RawBytesToASTObjectCompilationStage(ObjectToObjectCompilationStage[bytes, Node]):
    """Abstract compilation stage that turns raw bytes containing the input
    in some input format into an in-memory abstract syntax tree.
    """

    label = "reading..."

    _input: bytes
    _output: Optional[Node]

    def __init__(self, input: bytes):
        """Constructor.

        Parameters:
            input: the raw bytes containing the input
        """
        super().__init__()
        self._input = input
        self._output = None

    @property
    def input(self) -> bytes:
        return self._input

    @property
    def output(self) -> Node:
        if self._output is None:
            raise RuntimeError("stage was not executed yet")
        return self._output

    def run(self, environment: CompilationStageExecutionEnvironment) -> None:
        self._output = self._create_output(self.input_object, environment)

    @abstractmethod
    def _create_output(
        self, input: bytes, environment: CompilationStageExecutionEnvironment
    ) -> Node:
        raise NotImplementedError


class LEDSourceCodeToASTObjectCompilationStage(RawBytesToASTObjectCompilationStage):
    """Compilation stage that turns Python source code given as raw bytes into
    an abstract syntax tree representation of the LED controller program in memory.
    """

    def _create_output(
        self, input: bytes, environment: CompilationStageExecutionEnvironment
    ) -> Node:
        context = ExecutionContext()
        code = compile(input, "<<bytecode>>", "exec")
        context.evaluate(code, add_end_command=True)
        return context.ast


class BytecodeToASTObjectCompilationStage(RawBytesToASTObjectCompilationStage):
    """Compilation stage that turns compiled bytecode back into an abstract
    syntax tree representation of the LED controller program in memory.
    """

    def _create_output(
        self, input: bytes, environment: CompilationStageExecutionEnvironment
    ) -> Node:
        return BytecodeParser().parse(input)


class JSONBytecodeToASTObjectCompilationStage(RawBytesToASTObjectCompilationStage):
    """Compilation stage that turns compiled bytecode in JSON format back into
    an abstract syntax tree representation of the LED controller program in
    memory.
    """

    def _create_output(
        self, input: bytes, environment: CompilationStageExecutionEnvironment
    ) -> Node:
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

    _ast: Node
    optimiser: ASTOptimiser

    def __init__(self, ast: Node, optimiser: ASTOptimiser):
        """Constructor.

        Parameters:
            ast: the root of the abstract syntax tree that the compiler will
                optimise.
            optimiser: the optimiser to use
        """
        super().__init__()
        self._ast = ast
        self.optimiser = optimiser

    @property
    def input(self) -> Node:
        return self._ast

    @property
    def output(self) -> Node:
        return self._ast

    def run(self, environment: CompilationStageExecutionEnvironment) -> None:
        self.optimiser.optimise(self.input_object)


class ASTObjectToRawBytesCompilationStage(ObjectToObjectCompilationStage[Node, bytes]):
    """Abstract compilation stage that turns an in-memory abstract syntax tree
    into some output format as raw bytes.
    """

    label = "writing..."

    _input: Union[Node, ObjectTargetMixin[Node]]
    _output: Optional[bytes]

    def __init__(self, input: Union[Node, ObjectTargetMixin[Node]]):
        """Constructor.

        Parameters:
            input: the in-memory abstract syntax tree
        """
        super().__init__()
        self._input = input
        self._output = None

    @property
    def input(self):
        return self._input

    @property
    def output(self) -> bytes:
        if self._output is None:
            raise RuntimeError("stage was not executed yet")
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

    def _create_output(
        self, input: Node, environment: CompilationStageExecutionEnvironment
    ):
        return input.to_bytecode()


class ASTObjectToJSONBytecodeCompilationStage(ASTObjectToRawBytesCompilationStage):
    """Compilation stage that turns an in-memory abstract syntax tree from a
    file into a JSON file that contains the raw bytecode in base64-encoded
    format.
    """

    def _create_output(
        self, input: Node, environment: CompilationStageExecutionEnvironment
    ):
        from base64 import b64encode
        from json import dumps

        bytecode = input.to_bytecode()
        return dumps(
            {"version": 1, "data": b64encode(bytecode).decode("ascii")},
            indent=2,
            sort_keys=True,
        ).encode("ascii")


class ASTObjectToLEDSourceCodeCompilationStage(ASTObjectToRawBytesCompilationStage):
    """Compilation stage that turns an in-memory abstract syntax tree back into a
    (functionally equivalent) ``.led`` file.
    """

    def _create_output(
        self, input: Node, environment: CompilationStageExecutionEnvironment
    ):
        output = input.to_led_source().encode("utf-8")
        if output:
            output += b"\n"
        return output
