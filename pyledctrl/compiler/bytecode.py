"""Functions that roughly correspond to the bytecode statements and emit
abstract syntax tree fragments."""

from pyledctrl.compiler import ast
from pyledctrl.compiler.colors import parse_color
from pyledctrl.compiler.errors import InvalidDurationError, \
    MarkerNotResolvableError, FeatureNotImplementedError


def _check_easing_is_supported(easing):
    """Checks whether the given easing mode is supported.

    Raises:
        FeatureNotImplementedError: if the easing mode is not supported
    """
    if easing is not ast.EasingMode.LINEAR:
        raise FeatureNotImplementedError("only linear easing is supported")


class Marker(object):
    """Superclass for marker objects placed in the bytecode stream that are
    resolved to actual bytecode in a later compilation stage."""

    def to_ast_node(self):
        """Returns the abstract syntax tree node that should replace the marker
        in the abstract syntax tree.

        Returns:
            ast.Node or None: the absrtact syntax tree node that should replace
                the marker or None if the marker should be removed from the
                abstract syntax tree

        Raises:
            MarkerNotResolvableError: if the marker does not "know" all the
                information that is needed to produce a corresponding abstract
                syntax tree node.
        """
        return None


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

    def resolve_to_address(self, address):
        assert self.address is None
        self.address = address

    def to_ast_node(self):
        if self.address is None:
            raise MarkerNotResolvableError(self)
        else:
            return ast.JumpCommand(address=self.address)

    def __repr__(self):
        return "{0.__class__.__name__}(destination={0.destination!r})".format(self)


class UnconditionalJumpMarker(JumpMarker):
    """Marker object for an unconditional jump instruction."""
    pass


def end():
    return ast.EndCommand()


def fade_to_black(duration=None, easing=None):
    duration = _to_duration(duration)
    easing = ast.EasingMode.get(easing)
    _check_easing_is_supported(easing)
    return ast.FadeToBlackCommand(duration=duration)


def fade_to_color(red, green=None, blue=None, duration=None, easing=None):
    if green is None and blue is None:
        red, green, blue = parse_color(red)
    if red == green and green == blue:
        return fade_to_gray(red, duration, easing)
    duration = _to_duration(duration)
    easing = ast.EasingMode.get(easing)
    _check_easing_is_supported(easing)
    return ast.FadeToColorCommand(color=ast.RGBColor(red, green, blue),
                                  duration=duration)


def fade_to_gray(value, duration=None, easing=None):
    if value == 0:
        return fade_to_black(duration, easing)
    elif value == 255:
        return fade_to_white(duration, easing)
    else:
        duration = _to_duration(duration)
        easing = ast.EasingMode.get(easing)
        _check_easing_is_supported(easing)
        return ast.FadeToGrayCommand(value=value, duration=duration)


def fade_to_white(duration=None, easing=None):
    duration = _to_duration(duration)
    easing = ast.EasingMode.get(easing)
    _check_easing_is_supported(easing)
    return ast.FadeToWhiteCommand(duration=duration)


def jump(destination):
    return UnconditionalJumpMarker(destination)


def label(name):
    return LabelMarker(name)


def nop():
    return ast.NopCommand()


def set_black(duration=None):
    return ast.SetBlackCommand(duration=_to_duration(duration))


def set_color(red, green=None, blue=None, duration=None):
    if green is None and blue is None:
        red, green, blue = parse_color(red)
    if red == green and green == blue:
        return set_gray(red, duration)
    return ast.SetColorCommand(color=ast.RGBColor(red, green, blue),
                               duration=_to_duration(duration))


def set_gray(value, duration=None):
    if value == 0:
        return set_black(duration)
    elif value == 255:
        return set_white(duration)
    else:
        return ast.SetGrayCommand(duration=_to_duration(duration))


def set_white(duration=None):
    return ast.SetWhiteCommand(duration=_to_duration(duration))


def sleep(duration):
    return ast.SleepCommand(duration=_to_duration(duration))


def _to_duration(seconds):
    """Converts the given duration (specified in seconds) into the number
    of frames (assuming 50 frames per second); this is the format that is
    expected by the bytecode."""
    if seconds is None:
        seconds = 0
    return int(seconds * 50.0)
