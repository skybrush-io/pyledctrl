"""Functions that emit bytecode fragments."""

from __future__ import absolute_import

from .colors import parse_color
from .errors import InvalidDurationError, MarkerNotResolvableError


class CommandCode(object):
    END = b'\x00'
    NOP = b'\x01'
    SLEEP = b'\x02'
    WAIT_UNTIL = b'\x03'
    SET_COLOR = b'\x04'
    SET_GRAY = b'\x05'
    SET_BLACK = b'\x06'
    SET_WHITE = b'\x07'
    FADE_TO_COLOR = b'\x08'
    FADE_TO_GRAY = b'\x09'
    FADE_TO_BLACK = b'\x0A'
    FADE_TO_WHITE = b'\x0B'
    LOOP_BEGIN = b'\x0C'
    LOOP_END = b'\x0D'
    RESET_TIMER = b'\x0E'
    JUMP = b'\x0F'


class EasingMode(object):
    LINEAR = b'\x00'
    IN_SINE = b'\x01'
    OUT_SINE = b'\x02'
    IN_OUT_SINE = b'\x03'
    IN_QUAD = b'\x04'
    OUT_QUAD = b'\x05'
    IN_OUT_QUAD = b'\x06'
    IN_CUBIC = b'\x07'
    OUT_CUBIC = b'\x08'
    IN_OUT_CUBIC = b'\x09'
    IN_QUART = b'\x0A'
    OUT_QUART = b'\x0B'
    IN_OUT_QUART = b'\x0C'
    IN_QUINT = b'\x0D'
    OUT_QUINT = b'\x0E'
    IN_OUT_QUINT = b'\x0F'
    IN_EXPO = b'\x10'
    OUT_EXPO = b'\x11'
    IN_OUT_EXPO = b'\x12'
    IN_CIRC = b'\x13'
    OUT_CIRC = b'\x14'
    IN_OUT_CIRC = b'\x15'
    IN_BACK = b'\x16'
    OUT_BACK = b'\x17'
    IN_OUT_BACK = b'\x18'
    IN_ELASTIC = b'\x19'
    OUT_ELASTIC = b'\x1A'
    IN_OUT_ELASTIC = b'\x1B'
    IN_BOUNCE = b'\x1C'
    OUT_BOUNCE = b'\x1D'
    IN_OUT_BOUNCE = b'\x1E'

    @classmethod
    def get(cls, spec):
        if spec is None:
            return cls.LINEAR
        if isinstance(spec, int):
            return spec
        spec = spec.upper().replace("-", "_")
        return getattr(cls, spec)


class Marker(object):
    """Superclass for marker objects placed in the bytecode stream that are
    resolved to actual bytecode in a later compilation stage."""

    def as_bytecode(self):
        """Returns the bytecode that should be inserted into the bytecode
        stream in place of the marker.

        Returns:
            list of bytes: a list containing the bytes to be inserted into
                the bytecode

        Raises:
            MarkerNotResolvableError: if the marker does not "know" all the
                information that is needed to produce a bytecode representation.
        """
        return []


class LabelMarker(Marker):
    """Marker object for a label that jump instructions can refer to."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "{0.__class__.__name__}(name={0.name!r})".format(self)


class JumpMarker(Marker):
    """Marker object for a jump instruction."""

    def __init__(self, destination):
        self.destination = destination
        self.address = None

    def as_bytecode(self):
        if self.address is None:
            raise MarkerNotResolvableError(self)
        else:
            return CommandCode.JUMP, _to_varint(self.address)

    def resolve_to_address(self, address):
        assert self.address is None
        self.address = address

    def __repr__(self):
        return "{0.__class__.__name__}(destination={0.destination!r})".format(self)


class UnconditionalJumpMarker(JumpMarker):
    """Marker object for an unconditional jump instruction."""
    pass


def end():
    return CommandCode.END


def fade_to_black(duration=None, easing=None):
    duration = _to_duration_char(duration)
    easing = EasingMode.get(easing)
    return CommandCode.FADE_TO_BLACK, duration, easing


def fade_to_color(red, green=None, blue=None, duration=None, easing=None):
    if green is None and blue is None:
        red, green, blue = parse_color(red)
    if red == green and green == blue:
        return fade_to_gray(red, duration, easing)
    rgb_code = _to_char(red, green, blue)
    duration = _to_duration_char(duration)
    easing = EasingMode.get(easing)
    return CommandCode.FADE_TO_COLOR, rgb_code, duration, easing


def fade_to_gray(value, duration=None, easing=None):
    if value == 0:
        return fade_to_black(duration, easing)
    elif value == 255:
        return fade_to_white(duration, easing)
    else:
        duration = _to_duration_char(duration)
        easing = EasingMode.get(easing)
        return CommandCode.FADE_TO_GRAY, _to_char(value), duration, easing


def fade_to_white(duration=None, easing=None):
    duration = _to_duration_char(duration)
    easing = EasingMode.get(easing)
    return CommandCode.FADE_TO_WHITE, duration, easing


def jump(destination):
    return UnconditionalJumpMarker(destination)


def label(name):
    return LabelMarker(name)


def nop():
    return CommandCode.NOP


def set_black(duration=None):
    duration = _to_duration_char(duration)
    return CommandCode.SET_BLACK, duration


def set_color(red, green=None, blue=None, duration=None):
    if green is None and blue is None:
        red, green, blue = parse_color(red)
    if red == green and green == blue:
        return set_gray(red, duration)
    rgb_code = _to_char(red, green, blue)
    duration = _to_duration_char(duration)
    return CommandCode.SET_COLOR, rgb_code, duration


def set_gray(value, duration=None):
    if value == 0:
        return set_black(duration)
    elif value == 255:
        return set_white(duration)
    else:
        duration = _to_duration_char(duration)
        return CommandCode.SET_GRAY, _to_char(value), duration


def set_white(duration=None):
    duration = _to_duration_char(duration)
    return CommandCode.SET_WHITE, duration


def loop_begin(body, iterations=None):
    return CommandCode.LOOP_BEGIN, _to_char(iterations)


def loop_end():
    return CommandCode.LOOP_END


def _to_byte(value):
    """Converts the given value to a byte between 0 and 255."""
    if value is None:
        return 0
    return max(min(int(round(value)), 255), 0)


def _to_char(*values):
    """Converts the given value or values to bytes between 0 and 255, then
    casts them into characters."""
    return bytes(bytearray([_to_byte(value) for value in values]))


def _to_duration_char(seconds):
    """Converts the given duration (specified in seconds) into a duration byte
    that is typically used in the bytecode.

    The bytecode can encode integer seconds up to 191 (inclusive) and
    fractional seconds up to 1.28 seconds in units of 1/50 seconds."""
    if seconds is None:
        seconds = 0
    if seconds < 0 or seconds >= 192:
        raise InvalidDurationError(seconds)
    if int(seconds) == seconds:
        return _to_char(seconds)
    frames = int(seconds * 50.0)
    if frames > 0x3F:
        raise InvalidDurationError(seconds)
    return _to_char((frames & 0x3F) + 0xC0)


def _to_varint(value):
    """Converts the given numeric value into its varint representation."""
    result = []
    while value > 0:
        if value < 128:
            result.append(value)
        else:
            result.append(value & 0x7F + 0x80)
        value >>= 7
    return bytes(bytearray(result))
