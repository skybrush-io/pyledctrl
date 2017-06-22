"""Utility objects and functions for the compiler."""

from bisect import bisect, bisect_left
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

    Additionally, the object may keep track of a set of markers that will
    be inserted into the collection of lines when the timer passes a given
    timestamp.
    """

    def __init__(self, out, fps=25):
        """Constructor.

        Parameters:
            out (file-like): file-like object to write the collected lines
                into
            fps (int): number of frames per second
        """
        self._add_timestamps = True
        self._markers = []
        self._marker_index = 0
        self._timer = 0
        self.out = out
        self.fps = fps

    def add(self, line, duration):
        """Adds a new line to the line collector object.

        Parameters:
            line (str): the line to add
            duration (int): the duration of the execution of the line,
                in frames
        """
        if duration > 0:
            self._print_markers_until(self._timer + 1)

        self.out.write(self._format_line(line, self._timer))
        self._advance_by(duration)

    def add_marker(self, marker, time):
        """Adds a marker object to be inserted into the collection of lines
        when the internal timer passes the given timestamp.

        Parameters:
            marker (str): the marker line to insert when the time comes
            time (int): the timestamp corresponding to the marker line,
                in frames
        """
        item = time, marker
        index = bisect(self._markers, item)
        self._markers.insert(index, item)
        if index < self._marker_index:
            self._marker_index += 1
        elif index == self._marker_index:
            if self._markers[index][0] <= self._timer:
                self._marker_index += 1

    def close(self):
        """Closes the line collector object and flushes all remaining
        markers into the output.
        """
        if self._markers:
            max_time = max(time for time, _ in self._markers) + 1
            if max_time > self._timer:
                self._advance_to(max_time)

    @property
    def timer(self):
        """The state of the current timer, in frames."""
        return self._timer

    def _advance_by(self, frames):
        next_timer = self._timer + frames
        self._print_markers_until(next_timer)
        self._timer = next_timer

    def _advance_to(self, frame):
        diff = frame - self._timer
        if diff < 0:
            raise ValueError("Cannot go back in time")
        self._advance_by(diff)

    def _format_line(self, line, timestamp=None):
        """Formats the given line in a way that is suitable for the
        output.

        Parameters:
            line (str): the line to format
            timestamp (Optional[int]): the timestamp of the line, in frames,
                or ``None`` if the line has no timestamp

        Returns:
            str: the formatted line
        """
        if self._add_timestamps and timestamp is not None:
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

    def _print_markers_until(self, timer):
        next_index = bisect_left(self._markers, (timer, None))
        for i in xrange(self._marker_index, next_index):
            timestamp, marker = self._markers[i]
            self.out.write(self._format_line(marker))
        self._marker_index = next_index
