"""Exceptions thrown by the bytecode compiler."""


class CompilerError(RuntimeError):
    """Base class for all errors thrown by the bytecode compiler."""

    pass


class FeatureNotImplementedError(CompilerError):
    """Exception thrown when the compiler encounters a feature that has not
    been implemented yet."""

    pass


class UnsupportedInputFormatError(RuntimeError):
    """Exception thrown when the input file format is not supported by the
    compiler."""

    def __init__(self, format, message=None):
        self.format = format
        message = message or "Unsupported file format: {0}".format(format)
        super(UnsupportedInputFormatError, self).__init__(message)


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


class InvalidASTFormatError(RuntimeError):
    """Exception thrown when the compiler tries to parse an AST file with an
    invalid or unsupported format."""

    def __init__(self, filename, format, message=None):
        self.filename = filename
        self.format = format
        message = message or self._get_default_message()
        super(InvalidASTFormatError, self).__init__(message)

    def _get_default_message(self):
        if self.format is None:
            return "The AST file {0.filename!r} has an unknown format".format(self)
        else:
            return (
                "The AST file {0.filename!r} has an unknown format: "
                "{0.format!r}".format(self)
            )


class BytecodeParserError(RuntimeError):
    """Exception thrown for all sorts of parsing errors when reading bytecode
    representation of an AST from a stream.
    """

    pass


class BytecodeParserEOFError(BytecodeParserError):
    """Exception thrown when trying to read some bytecode object from a stream
    and the end of the stream has been reached.
    """

    def __init__(self, cls, message=None):
        """Constructor.

        Parameters:
            cls (callable): the AST node class that we have tried to read
        """
        self.cls = cls
        message = message or self._get_default_message()
        super(BytecodeParserEOFError, self).__init__(message)

    def _get_default_message(self):
        if self.cls is None:
            return "EOF reached while parsing bytecode"
        else:
            return "EOF reached while parsing {0} from bytecode".format(
                getattr(self.cls, "__name__", "unknown class instance")
            )
