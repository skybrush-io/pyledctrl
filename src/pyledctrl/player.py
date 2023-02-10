"""Bytecode player that takes an abstract syntax tree representing a light
program and that can tell the color of the light program at any given time
instant.
"""

from collections import deque
from math import isfinite
from typing import Iterator, Optional, Tuple

from .compiler import compile
from .compiler.formats import InputFormat, InputFormatLike, OutputFormat
from .executor import Color, Executor, ExecutorState

__all__ = ("Player",)


_START = ExecutorState(timestamp=-0.00001, color=Color.BLACK)
_END = ExecutorState(timestamp=float("inf"), color=Color.BLACK)


class Player:
    """Object that takes a LedCtrl light program in its abstract syntax tree
    format and can then answer queries about the color of the light program at
    any point in time, or iterate over the light program with a fixed number of
    frames per second.
    """

    @classmethod
    def from_bytes(
        cls, data: bytes, format: InputFormatLike = InputFormat.LEDCTRL_BINARY
    ):
        """Creates a bytecode player object that will play the given light
        program.

        Parameters:
            data: the light program to play
            format: the format of the input
        """
        ast = compile(data, input_format=format, output_format=OutputFormat.AST)
        return cls(ast=ast)

    @classmethod
    def from_file(cls, filename: str, format: Optional[InputFormatLike] = None):
        """Creates a bytecode player object that will play the bytecode found
        in the given file.

        Parameters:
            filename: name of the file to load
            format: the format of the input; `None` means autodetection from the
                extension of the file
        """
        return cls(
            ast=compile(filename, input_format=format, output_format=OutputFormat.AST)
        )

    @classmethod
    def from_json(cls, data: dict, format: InputFormatLike = InputFormat.LEDCTRL_JSON):
        """Creates a bytecode player object that will play the given light
        program in JSON format.

        Parameters:
            data: the light program to play
            format: the format of the input
        """
        ast = compile(data, input_format=format, output_format=OutputFormat.AST)
        return cls(ast=ast)

    def __init__(self, ast=None):
        """Constructor.

        Parameters:
            ast: the abstract syntax tree of the light program to play
        """
        self._ast = ast
        self._rewind()

    @property
    def ended(self) -> bool:
        """Returns whether the current light sequence has ended."""
        return self._event_iter is None

    def get_color_at(self, timestamp: float) -> Color:
        """Returns the color that the light program emits at the given
        timestamp.
        """
        if not isfinite(timestamp):
            raise ValueError("infinite timestamp not supported")

        # Do we need to rewind?
        if self._events and timestamp < self._events[0].timestamp:
            self._rewind()

        # Fast-forward to the given timestamp and feed the event queue
        while timestamp >= self._last_event_time:
            self._get_next_event()

        # At this point, we can be sure that the event queue has at least two
        # items (we put the _START element in there first, and in the worst
        # case we have exhausted the light program immediately, also placing
        # _END in the queue)

        # Optimize for the common case: timestamp is almost always somewhere
        # between the last two items in the event queue, so scan from the
        # back
        ev = self._events
        index = len(ev) - 2
        while index > 0 and timestamp < ev[index].timestamp:
            index -= 1

        start, end = ev[index], ev[index + 1]
        if end.is_fade:
            diff = end.timestamp - start.timestamp
            ratio = (timestamp - start.timestamp) / diff
            color = start.color.mix_with(end.color, ratio=ratio, integral=True)
        else:
            color = start.color

        return color

    def iterate(self, fps: int = 25) -> Iterator[Tuple[float, Color]]:
        """Iterates over the light program and produces an iterable of pairs
        consisting of a timestamp (in seconds) and the corresponding RGB color.

        Parameters:
            fps: the number of frames per second to generate

        Yields:
            a timestamp-color pair for each frame
        """
        self._rewind()

        seconds, frames, t, dt = 0, 0, 0, 1.0 / fps

        while not self.ended:
            yield t, self.get_color_at(t)
            t += dt
            frames += 1
            if frames == fps:
                seconds, frames = seconds + 1, 0
                t = seconds

    def to_bytes(self) -> bytes:
        """Returns the light program encoded in LedCtrl format."""
        return self._ast.to_bytecode()

    def _get_next_event(self) -> None:
        """Retrieves the next event from the executor and stores it in the
        event queue.
        """
        if not self.ended:
            event = next(self._event_iter, _END)
            event.timestamp = float(event.timestamp)
            self._events.append(event)
            if event is _END:
                self._event_iter = None
            self._last_event_time = event.timestamp

    def _rewind(self) -> None:
        """Rewinds the execution of the bytecode to zero time."""
        self._events = deque([_START], maxlen=32)
        self._last_event_time = -1
        self._event_iter = Executor().execute(self._ast) if self._ast else iter([])
