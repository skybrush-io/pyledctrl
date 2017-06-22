"""Utility objects and functions for the compiler."""

from time import time


def get_timestamp_of(obj, default_value=None):
    """Returns the timestamp of the given object if it is timestamped; returns
    the given default value otherwise.

    Parameters:
        obj (object): the object whose timestamp is to be returned
        default_value (object): the default timestamp to return if the object
            is not timestamped or if it has no timestamp

    Returns:
        object: the timestamp of the object or the default value if the object
            is not timestamped or if it has no timestamp
    """
    return getattr(obj, "timestamp", default_value)


def is_timestamped(obj):
    """Returns whether a given object is timestamped.

    An object is timestamped if it has a ``timestamp`` property that returns
    a UNIX timestamp.
    """
    return hasattr(obj, "timestamp")


class TimestampWrapper(object):
    """Wrapper object that wraps another object and adds a ``timestamp``
    property to it to make it timestamped.
    """

    @classmethod
    def wrap(cls, wrapped, timestamp=None):
        """Creates a new timestamped wrapper for the given wrapped object.

        Parameters:
            wrapped (object): the object to wrap
            timestamp (Optional[float]): the timestamp added to the object;
                ``None`` means to add the current time.
        """
        if timestamp is None:
            timestamp = time()
        return cls(wrapped, timestamp)

    def __init__(self, wrapped, timestamp):
        """Constructor.

        Parameters:
            wrapped (object): the object to wrap
            timestamp (loat): the timestamp added to the object.
        """
        self._wrapped = wrapped
        self._timestamp = float(timestamp)

    def __getattr__(self, attr):
        return getattr(self._wrapped, attr)

    @property
    def wrapped(self):
        """The object wrapped by this wrapper."""
        return self._wrapped


class TimestampedLineCollector(object):
    """Helper object that allows us to collect lines to be printed into a
    ``.led`` output file and also keep track of a running timer such that
    each added line is timestamped with the state of the timer at the
    time the line will be executed.
    """

    def __init__(self, fps=25):
        """Constructor.

        Parameters:
            fps (int): number of frames per second
        """
        self._add_timestamps = True
        self._lines = []
        self._timer = 0
        self.fps = fps

    def add(self, line, duration):
        """Adds a new line to the line collector object.

        Parameters:
            line (str): the line to add
            duration (int): the duration of the execution of the line,
                in frames
        """
        self._lines.append((line, self._timer))
        self._timer += duration

    def flush(self, fp):
        """Flushes the lines collected so far into the given file-like
        object.
        """
        for line, timestamp in self._lines:
            fp.write(self._format_line(line, timestamp))
        self._lines = []

    @property
    def timer(self):
        """The state of the current timer, in frames."""
        return self._timer

    def _format_line(self, line, timestamp):
        """Formats the given line in a way that is suitable for the
        output.

        Parameters:
            line (str): the line to format
            timestamp (int): the timestamp of the line, in frames

        Returns:
            str: the formatted line
        """
        if self._add_timestamps:
            if len(line) < 60:
                line += " " * (60 - len(line))
            line += "# " + self._format_frame_count_as_time(timestamp)
        return line + "\n"

    def _format_frame_count_as_time(self, frames):
        seconds, residual = divmod(frames, self.fps)
        minutes, seconds = divmod(seconds, 60)
        return "{minutes}:{seconds:02}+{residual:02} ({frames} frames)".format(
            minutes=int(minutes), seconds=int(seconds),
            residual=int(residual), frames=int(frames)
        )
