"""Utility objects and functions for the compiler."""

from __future__ import division

from bisect import bisect, bisect_left
from time import time

from pyledctrl.parsers.sunlite import Time


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
        self._formatted_ticks_cache = {}
        self._fps = None
        self._markers = []
        self._marker_index = 0
        self._timer = 0
        self.out = out
        self.fps = fps

    def add(self, line, duration=0):
        """Adds a new line to the line collector object.

        The token ``@DT@`` in the line will be replaced by the duration
        in *seconds*.

        Parameters:
            line (str): the line to add
            duration (decimal.Decimal): the duration of the execution of
                the line, in frames
        """
        if duration > 0:
            self._print_markers_until(self._timer + 1)

        line = line.replace("@DT@", str(duration / self.fps))
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
    def fps(self):
        """Number of frames per second."""
        return self._fps

    @fps.setter
    def fps(self, value):
        if self._fps == value:
            return

        self._fps = value
        self._formatted_ticks_cache = {}

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
        result = self._formatted_ticks_cache.get(frames)
        if not result:
            seconds, residual = divmod(frames, self.fps)
            minutes, seconds = divmod(seconds, 60)
            result = "{minutes}:{seconds:02}+{residual:02} " "({frames} frames)".format(
                minutes=int(minutes),
                seconds=int(seconds),
                residual=int(residual),
                frames=int(frames),
            )
            self._formatted_ticks_cache[frames] = result
        return result

    def _print_markers_until(self, timer):
        next_index = bisect_left(self._markers, (timer, None))
        for i in range(self._marker_index, next_index):
            timestamp, marker = self._markers[i]
            self.out.write(self._format_line(marker))
        self._marker_index = next_index


class UnifiedTimeline(object):
    """Unified timeline object that contains a time axis with time instant.
    and a list of associated channel values for each time instant. The time
    instants have the following properties:

    - ``time`` - the time, in frames

    - ``fade`` - fade time into the time instant, in frames

    - ``wait`` - wait time after the time instant, in frames
    """

    @classmethod
    def from_times_and_channels(cls, iterable):
        """Constructs a unified timeline from an iterable that yields
        pairs of time instants and channel values. The time instants
        yielded by the iterable must be sorted.
        """
        result = cls()
        result.times, result.channels = zip(*iterable)

    def __init__(self):
        """Constructor."""
        self._last_time = -1
        self.times = []
        self.channels = []

    def add(self, time, channels):
        """Adds a new time instant with the corresponding channel values.

        Parameters:
            time (Time): the time instant
            channels (Iterable[int]): the channel values corresponding to
                the time instant
        """
        if time.time >= self._last_time:
            self.times.append(time)
            self.channels.append(list(channels))
        else:
            raise ValueError("UnifiedTimeline.add() must be called in " "sorted order")
        self._last_time = time.time

    def ensure_min_channel_count(self, num_channels):
        """Ensures that there are at least the given number of channels for
        each time instant in the timeline.

        Parameters:
            num_channels (int): the minimum number of channels
        """
        for values in self.channels:
            if len(values) < num_channels:
                values.extend([0] * (num_channels - len(values)))

    def set_channel_value_at(self, time, channel_index, value):
        """Sets the value of the channel with the given index to the given
        value on the time axis.

        Parameters:
            time (int): the time instant
            channel_index (int): the channel index
            value (int): the channel value
        """
        place = self._find_time(time)
        self.channels[place][channel_index] = value

    def set_channel_value_in_range(self, start, end, channel_index, value):
        """Sets the value of the channel with the given index to the given
        value on the time axis in the given range.

        Parameters:
            start (int): the start time
            end (int): the end time
            channel_index (int): the channel index
            value (int): the channel value
        """
        start_index = self._find_time(start)
        if end is not None:
            end_index = self._find_time(end)
        else:
            end_index = len(self.times)
        for place in range(start_index, end_index):
            self.channels[place][channel_index] = value

    def shift_to_left(self, frames):
        """Shift the entire timeline and all its time points to the left
        (i.e. into the past) by the given number of frames.

        Time points that are moved before T=0 will be removed.

        Parameters:
            frames (int): the number of frames to shift by
        """
        if frames == 0:
            return

        place = self._find_time(frames)
        self.times[:place] = []
        self.channels[:place] = []
        for time_instant in self.times:
            time_instant.time -= frames

    def _find_time(self, time):
        dummy_time = Time(time=time)
        place = bisect_left(self.times, dummy_time)
        if place >= len(self.times):
            # New timestamp has to be inserted at the end
            # TODO(ntamas): implement this
            raise NotImplementedError
        elif self.times[place].time != time:
            # Timestamp does not exist yet
            if place == 0:
                # New timestamp has to be inserted at the beginning
                next_time = self.times[0]
                dummy_time.wait = next_time.time - dummy_time.time
                new_channels = [0] * len(self.channels[0])
            else:
                prev_time = self.times[place - 1]
                prev_channels = self.channels[place - 1]

                # When a timestamp has both 'fade' and 'wait' times,
                # 'fade' comes first, followed by 'wait'. Therefore,
                # we will first consume frames from the 'wait' time of
                # the previous frame and then we consume from 'fade' time
                # only if we have consumed all the available 'wait' time

                # First we consume the wait time
                diff = prev_time.time + prev_time.fade + prev_time.wait - time
                wait_time_to_consume = min(prev_time.wait, diff)
                dummy_time.wait += wait_time_to_consume
                prev_time.wait -= wait_time_to_consume
                diff -= wait_time_to_consume
                new_channels = list(prev_channels)

                # Now we consume the fade time
                if diff > 0:
                    fade_time_to_consume = min(prev_time.fade, diff)
                    ratio = fade_time_to_consume / prev_time.fade
                    dummy_time.fade += fade_time_to_consume
                    prev_time.fade -= fade_time_to_consume
                    next_channels = self.channels[place]
                    new_channels = [
                        (1 - ratio) * next_channels[i] + ratio * new_channels[i]
                        for i in range(len(new_channels))
                    ]
                    diff -= fade_time_to_consume

                if diff > 0:
                    # This should not have happened
                    raise ValueError("inconsistent timeline")

                # Make sure that pyro channels are not interpolated
                if len(new_channels) >= 3:
                    new_channels[3:] = prev_channels[3:]

            self.times.insert(place, dummy_time)
            self.channels.insert(place, new_channels)

        return place

    def __iter__(self):
        return zip(self.times, self.channels)
