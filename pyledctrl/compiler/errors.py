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


class DuplicateLabelError(RuntimeError):
    """Exception thrown when the input file contains a duplicate label."""

    def __init__(self, label, message=None):
        self.label = label
        message = message or "Duplicate label in input: {0!r}".format(label)
        super(DuplicateLabelError, self).__init__(message)


class MarkerNotResolvableError(CompilerError):
    """Exception thrown by a marker when the marker cannot be replaced with "real"
    bytecode in the bytecode stream, most likely because the marker does not "know"
    all the information it needs to replace itself with bytecode."""

    def __init__(self, marker, message=None):
        self.marker = marker
        message = message or "Marker not resolvable; {0!r}".format(marker)
        super(MarkerNotResolvableError, self).__init__(message)
