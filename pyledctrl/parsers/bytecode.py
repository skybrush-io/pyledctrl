"""Parser implementation for the LedCtrl bytecode format."""

from io import BufferedReader, BytesIO

from pyledctrl.compiler.ast import StatementSequence
from pyledctrl.compiler.errors import BytecodeParserError, BytecodeParserEOFError

__all__ = ("BytecodeParser", "BytecodeParserError", "BytecodeParserEOFError")


class BytecodeParser(object):
    """Parser implementation for the compiled LedCtrl bytecode format.

    This parser can be used to restore the abstract syntax tree (AST) of a
    compiled LedCtrl bytecode file. The AST can then be used to print a
    human-readable "source code" of the compiled LedCtrl bytecode.
    """

    def parse(self, fp):
        """Parses the given input and returns a data structure that represents
        the parsed abstract syntax tree.

        Parameters:
            fp (Union[bytes, IOBase]): the input to parse

        Returns:
            StatementSequence: the sequence of statements found in the input
        """
        if isinstance(fp, bytes):
            fp = BytesIO(fp)
        return StatementSequence.from_bytecode(BufferedReader(fp))
