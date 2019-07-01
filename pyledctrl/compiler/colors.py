"""Handling of color names and specifications in the compiler."""

from .errors import InvalidColorError


def parse_color(string):
    """Parses a string specification of a color and returns an RGB triplet.
    See the ``known_colors`` dict for the list of known color names.

    Color names are case insensitive. Leading and trailing whitespace is
    stripped.
    """
    try:
        string = string.lower().strip()
        return known_colors[string]
    except:
        raise InvalidColorError(string)


known_colors = {
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
}
