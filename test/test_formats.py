from pyledctrl.compiler.errors import UnsupportedInputFormatError
from pyledctrl.compiler.formats import InputFormat, OutputFormat

from pytest import raises


def test_input_format_from_filename():
    detect = InputFormat.detect_from_filename
    assert detect("x.bin") is InputFormat.LEDCTRL_BINARY
    assert detect("x.json") is InputFormat.LEDCTRL_JSON
    assert detect("x.led") is InputFormat.LEDCTRL_SOURCE
    assert detect("x.oled") is InputFormat.LEDCTRL_SOURCE
    assert detect("x.sbl") is InputFormat.LEDCTRL_BINARY

    with raises(UnsupportedInputFormatError):
        assert detect("x.foo")


def test_output_format_from_filename():
    detect = OutputFormat.detect_from_filename
    assert detect("x.bin") is OutputFormat.LEDCTRL_BINARY
    assert detect("x.json") is OutputFormat.LEDCTRL_JSON
    assert detect("x.led") is OutputFormat.LEDCTRL_SOURCE
    assert detect("x.oled") is OutputFormat.LEDCTRL_SOURCE
    assert detect("x.sbl") is OutputFormat.LEDCTRL_BINARY
    assert detect("x.foo") is OutputFormat.LEDCTRL_BINARY
