"""Executor for abstract syntax trees generated by the LedCtrl compiler."""

from __future__ import division

from collections import namedtuple
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from itertools import chain, count, groupby
from numbers import Number
from operator import attrgetter
from typing import Optional

from .compiler.ast import Duration
from .utils import consecutive_pairs, last

__all__ = ("Color", "ExecutorState", "Executor")


_Color = namedtuple("Color", "red green blue")
_Color.__new__.__defaults__ = (0, 0, 0)


class Color(_Color):
    """Color of LEDs on a LED strip."""

    @classmethod
    def black(cls):
        """Returns an instance of the color black."""
        return cls.BLACK

    @classmethod
    def gray(cls, value):
        """Returns an instance of the color gray with the given value."""
        return cls(red=value, green=value, blue=value)

    @classmethod
    def white(cls):
        """Returns an instance of the color white."""
        return cls.gray(255)

    def mix_with(self, other, ratio: float = 0.5, integral: bool = False):
        """Mixes the RGB components of this color with some other color,
        and returns a new color.

        Parameters:
            other: the other color to mix with this color
            ratio: the mixing ratio
            integral: whether the new RGB values should be rounded to the
                nearest integer

        Returns:
            the new, mixed color
        """
        if ratio <= 0:
            return self
        elif ratio >= 1:
            return other

        red = self.red * (1 - ratio) + other.red * ratio
        green = self.green * (1 - ratio) + other.green * ratio
        blue = self.blue * (1 - ratio) + other.blue * ratio

        if integral:
            red, green, blue = round(red), round(green), round(blue)

        return self.__class__(red=red, green=green, blue=blue)

    def update_from(self, obj):
        """Updates the color from another object that has ``red``, ``green``
        and ``blue`` properties containing numeric abstract syntax tree nodes,
        and returns the updated color.
        """
        return self._replace(
            red=obj.red.value, green=obj.green.value, blue=obj.blue.value
        )


Color.BLACK = Color.gray(0)


class ExecutorState:
    """Mutable state of an executor object."""

    def __init__(
        self, timestamp=0, color: Optional[Color] = None, is_fade: bool = False
    ):
        """Constructor.

        Parameters:
            timestamp: the initial timestamp
            color: the initial color (if any), defaults to black
        """
        self.timestamp = timestamp
        self.color = Color.black() if color is None else color
        self.is_fade = is_fade

    def advance_time_by(self, duration):
        """Increases the timestamp of the state with the given duration.

        Parameters:
            duration: the duration to increase the timestamp with; may be a
                number (which is treated as seconds), or a Duration AST node
        """
        if not isinstance(duration, Number):
            # We assume that 'duration' is a numeric AST node and its value
            # gives the duration in units specified by Duration.FPS
            duration = duration.value / Duration.FPS
        else:
            # We assume that 'duration' specifies the duration in seconds
            pass
        self.timestamp += duration

    def copy(self):
        """Returns an independent copy of this state object."""
        return self.__class__(
            timestamp=self.timestamp, color=self.color, is_fade=self.is_fade
        )


class StopExecution(Exception):
    """Exception raised by an executor to stop execution."""

    pass


def do_nothing(*args, **kwds):
    """Fake opcode handler for the executor in case we encounter an opcode that
    we don't need to react to.
    """
    return iter(())


class Executor:
    """Executor for abstract syntax trees generated by the LedCtrl compiler.

    The executor manages the state of a virtual LED strip with red, green and
    blue channels, and is able to execute the command represented by any
    abstract tree node on the virtual LED strip. The executor method yields
    state objects for each interesting point in the execution where a color
    change occurs.
    """

    def __init__(self):
        """Constructor.

        Creates a virtual LED strip set to black color at timestamp zero.
        """
        self.state = ExecutorState()

    def execute(self, node):
        """Executes the command(s) in the given abstract syntax tree node
        and updates the state accordingly, yielding the state after every
        timestamp change.

        Note that the state is copied before it is yielded back to the caller,
        so it is safe to mutate the state object outside the executor; it will
        not affect the executor itself.
        """
        try:
            for state in self._execute(node):
                yield state.copy()
        except StopExecution:
            pass

    def _execute(self, node):
        class_name = node.__class__.__name__
        method = getattr(self, "_execute_{0}".format(class_name), None)
        if method is None:
            raise RuntimeError("cannot execute {0}".format(class_name))

        for state in method(node):
            yield state

    def _execute_EndCommand(self, node):
        raise StopExecution()

    def _execute_FadeToBlackCommand(self, node):
        for state in self._fade_to(Color.black(), node.duration):
            yield state

    def _execute_FadeToColorCommand(self, node):
        for state in self._fade_to(
            Color(
                red=node.color.red.value,
                green=node.color.green.value,
                blue=node.color.blue.value,
            ),
            node.duration,
        ):
            yield state

    def _execute_FadeToGrayCommand(self, node):
        for state in self._fade_to(Color.gray(node.value.value), node.duration):
            yield state

    def _execute_FadeToWhiteCommand(self, node):
        for state in self._fade_to(Color.white(), node.duration):
            yield state

    def _execute_LoopBlock(self, node):
        num_iterations = node.iterations.value
        if num_iterations > 0:
            iterator = range(num_iterations)
        else:
            iterator = count()
        for i in iterator:
            for state in self._execute(node.body):
                yield state

    def _execute_SetBlackCommand(self, node):
        self.state.color = Color.black()
        self.state.is_fade = False
        yield self.state
        self.state.advance_time_by(node.duration)

    def _execute_SetColorCommand(self, node):
        self.state.color = self.state.color.update_from(node.color)
        self.state.is_fade = False
        yield self.state
        self.state.advance_time_by(node.duration)

    def _execute_SetGrayCommand(self, node):
        self.state.color = Color.gray(node.value.value)
        self.state.is_fade = False
        yield self.state
        self.state.advance_time_by(node.duration)

    def _execute_SetWhiteCommand(self, node):
        self.state.color = Color.white()
        self.state.is_fade = False
        yield self.state
        self.state.advance_time_by(node.duration)

    def _execute_StatementSequence(self, node):
        for statement in node.statements:
            for state in self._execute(statement):
                yield state

    def _execute_SleepCommand(self, node):
        self.state.advance_time_by(node.duration)
        self.state.is_fade = False
        yield self.state

    def _execute_WaitUntilCommand(self, node):
        new_timestamp = node.timestamp.value
        self.state.timestamp = max(self.state.timestamp, new_timestamp)
        self.state.is_fade = False
        yield self.state

    _execute_NopCommand = do_nothing
    _execute_SetPyroCommand = do_nothing
    _execute_SetPyroAllCommand = do_nothing

    def _fade_to(self, color, duration):
        if not self.state.is_fade:
            yield self.state
            self.state.is_fade = True

        self.state.advance_time_by(duration)
        self.state.color = color
        yield self.state


def _frames_between(start: float, end: float, fps=Duration.FPS):
    """Returns an iterator yielding the timestamps of all 'whole' frames that
    fall between the given start and end times, excluding the endpoints.

    Parameters:
        start: the start time, in seconds
        end: the end time, in seconds
        fps (Decimal): number of frames per second

    Yields:
        float: timestamps between the given start and end time that correspond
            to whole frames
    """
    start_index = int((start * fps).to_integral_value(rounding=ROUND_DOWN))
    end_index = int((end * fps).to_integral_value(rounding=ROUND_UP))
    return (index / fps for index in range(start_index + 1, end_index))


def remove_duplicates(events):
    """Given a stream of timestamped events in ascending order, removes
    duplicate events that refer to the same time instant, except the last one.
    """
    for _, events in groupby(events, attrgetter("timestamp")):
        yield last(events)


def unroll(events, fps=Duration.FPS):
    return remove_duplicates(_unroll(events, fps))


def _unroll(events, fps):
    start = ExecutorState()
    fps = Decimal(fps)

    for prev_event, event in consecutive_pairs(chain([start], events)):
        if event.is_fade:
            event.is_fade = False
            start, end = prev_event.timestamp, event.timestamp
            length = end - start
            for timestamp in _frames_between(start, end):
                extra_event = event.copy()
                ratio = (timestamp - start) / length
                extra_event.color = prev_event.color.mix_with(
                    event.color, ratio=ratio, integral=True
                )
                extra_event.timestamp = timestamp
                yield extra_event
        yield event
