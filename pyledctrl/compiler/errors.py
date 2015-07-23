"""Exceptions thrown by the bytecode compiler."""


class CompilerError(RuntimeError):
    """Base class for all errors thrown by the bytecode compiler."""
    pass


class UnsupportedInputFileFormatError(RuntimeError):
    """Exception thrown when the input file format is not supported by the
    compiler."""

    def __init__(self, format, message=None):
        self.format = format
        message = message or "Unsupported file format: {0}".format(format)
        super(UnsupportedInputFileFormatError, self).__init__(message)


class InvalidColorError(RuntimeError):
    """Exception thrown when the input file contains an invalid or unknown
    color specification."""

    def __init__(self, color, message=None):
        self.color = color
        message = message or "Invalid color in input: {0!r}".format(color)
        super(InvalidColorError, self).__init__(message)


class InvalidDurationError(RuntimeError):
    """Exception thrown when the input file contains an invalid duration."""

    def __init__(self, duration, message=None):
        self.duration = duration
        message = message or "Invalid duration in input: {0!r}".format(duration)
        super(InvalidDurationError, self).__init__(message)
