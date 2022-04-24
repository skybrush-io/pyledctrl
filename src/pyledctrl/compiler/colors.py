"""Handling of color names and specifications in the compiler."""

from typing import Dict, Tuple

from .errors import InvalidColorError


Color = Tuple[int, int, int]


def parse_color(string: str) -> Color:
    """Parses a string specification of a color and returns an RGB triplet.
    See the ``known_colors`` dict for the list of known color names.

    Color names are case insensitive. Leading and trailing whitespace is
    stripped.

    Raises:
        InvalidColorError: if the string specification cannot be parsed
    """
    try:
        string = string.lower().strip()
        return known_colors[string]
    except Exception:
        raise InvalidColorError(string)


known_colors: Dict[str, Color] = {
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
}
