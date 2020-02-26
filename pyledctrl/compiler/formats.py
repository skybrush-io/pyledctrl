"""Enums corresponding to the input and output formats supported
by the compiler.
"""

import os

from enum import Enum
from typing import Union

from .errors import UnsupportedInputFormatError

__all__ = ("InputFormat", "InputFormatLike", "OutputFormat", "OutputFormatLike")


class InputFormat(Enum):
    """Enum representing the possible input formats supported by the
    compiler.
    """

    LEDCTRL_SOURCE = "ledctrl_source"
    LEDCTRL_BINARY = "ledctrl_binary"
    LEDCTRL_JSON = "ledctrl_json"
    SUNLITE_STUDIO_SCE = "sunlite_sce"
    SUNLITE_STUDIO_SES = "sunlite_ses"

    @staticmethod
    def detect_from_filename(filename: str):
        """Proposes an input format to use for a file with the given filename.

        Parameters:
            filename: the name of the file

        Returns:
            the proposed input format for the file

        Raises:
            UnsupportedInputFormatError: if the input format of the file cannot
                be detected
        """
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext in (".led", ".oled"):
            return InputFormat.LEDCTRL_SOURCE
        elif ext in (".bin", ".sbl"):
            return InputFormat.LEDCTRL_BINARY
        elif ext == ".json":
            return InputFormat.LEDCTRL_JSON
        elif ext == ".sce":
            return InputFormat.SUNLITE_STUDIO_SCE
        elif ext == ".ses":
            return InputFormat.SUNLITE_STUDIO_SES
        else:
            raise UnsupportedInputFormatError(filename=filename)


class OutputFormat(Enum):
    """Enum representing the possible output formats supported by the
    compiler.
    """

    LEDCTRL_SOURCE = "ledctrl_source"
    LEDCTRL_BINARY = "ledctrl_binary"
    LEDCTRL_JSON = "ledctrl_json"
    AST = "ast"

    @staticmethod
    def detect_from_filename(filename: str):
        """Proposes an output format to use for a file with the given filename.

        Parameters:
            filename: the name of the file

        Returns:
            the proposed output format for the file
        """
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext in (".led", ".oled"):
            return OutputFormat.LEDCTRL_SOURCE
        elif ext in (".bin", ".sbl"):
            return OutputFormat.LEDCTRL_BINARY
        elif ext == ".json":
            return OutputFormat.LEDCTRL_JSON
        else:
            return OutputFormat.LEDCTRL_BINARY


#: Type specification for objects that can be cast into an InputFormat
InputFormatLike = Union[InputFormat, str]

#: Type specification for objects that can be cast into an OutputFormat
OutputFormatLike = Union[OutputFormat, str]
