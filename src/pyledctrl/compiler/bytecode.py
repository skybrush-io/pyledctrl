"""Functions that roughly correspond to the bytecode statements and emit
abstract syntax tree fragments."""

from pyledctrl.compiler import ast
from pyledctrl.compiler.colors import parse_color

from .markers import LabelMarker, UnconditionalJumpMarker


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
