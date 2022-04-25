"""Functions that roughly correspond to the bytecode statements and emit
abstract syntax tree fragments."""

from pyledctrl.compiler import ast
from pyledctrl.compiler.colors import parse_color
from pyledctrl.compiler.errors import MarkerNotResolvableError


class Marker:
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
        self.destination_marker = None
        self.address = None

    def _resolve_to_address(self, address):
        assert self.address is None
        self.address = address

    def _resolve_to_marker(self, marker):
        assert self.destination_marker is None
        self.destination_marker = marker

    def resolve_to(self, address_or_marker):
        if isinstance(address_or_marker, int):
            self._resolve_to_address(address_or_marker)
        else:
            self._resolve_to_marker(address_or_marker)

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


def comment(value):
    return ast.Comment(value=value)


def end():
    return ast.EndCommand()


def fade_to_black(duration=None):
    duration = ast.Duration.from_seconds(duration)
    return ast.FadeToBlackCommand(duration=duration)


def fade_to_color(red, green=None, blue=None, duration=None):
    if green is None and blue is None:
        red, green, blue = parse_color(red)
    red, green, blue = int(round(red)), int(round(green)), int(round(blue))
    color = ast.RGBColor.cached(red, green, blue)
    duration = ast.Duration.from_seconds(duration)
    return ast.FadeToColorCommand(color=color, duration=duration)


def fade_to_gray(value, duration=None):
    duration = ast.Duration.from_seconds(duration)
    return ast.FadeToGrayCommand(value=value, duration=duration)


def fade_to_white(duration=None):
    duration = ast.Duration.from_seconds(duration)
    return ast.FadeToWhiteCommand(duration=duration)


def jump(destination):
    return UnconditionalJumpMarker(destination)


def label(name):
    return LabelMarker(name)


def nop():
    return ast.NopCommand()


def pyro_clear():
    return pyro_set_all()


def pyro_disable(*channels):
    mask = ast.ChannelMask(enable=False, channels=channels)
    return ast.SetPyroCommand(mask=mask)


def pyro_enable(*channels):
    mask = ast.ChannelMask(enable=True, channels=channels)
    return ast.SetPyroCommand(mask=mask)


def pyro_set_all(*channels):
    return ast.SetPyroAllCommand(values=ast.ChannelValues(channels))


def set_black(duration=None):
    return ast.SetBlackCommand(duration=ast.Duration.from_seconds(duration))


def set_color(red, green=None, blue=None, duration=None):
    if green is None and blue is None:
        red, green, blue = parse_color(red)
    red, green, blue = int(round(red)), int(round(green)), int(round(blue))
    return ast.SetColorCommand(
        color=ast.RGBColor.cached(red, green, blue),
        duration=ast.Duration.from_seconds(duration),
    )


def set_gray(value, duration=None):
    return ast.SetGrayCommand(duration=ast.Duration.from_seconds(duration))


def set_white(duration=None):
    return ast.SetWhiteCommand(duration=ast.Duration.from_seconds(duration))


def sleep(duration):
    return ast.SleepCommand(duration=ast.Duration.from_seconds(duration))


def wait_until(timestamp):
    return ast.WaitUntilCommand(timestamp=ast.Duration.from_seconds(timestamp))
