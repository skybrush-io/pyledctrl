import pytest

from pyledctrl.compiler.ast import (
    Duration,
    EndCommand,
    Node,
    NopCommand,
    SleepCommand,
    Varuint,
    WaitUntilCommand,
)


COMMANDS = [
    (EndCommand(), b"\x00", "end()"),
    (NopCommand(), b"\x01", "nop()"),
    (SleepCommand(duration=Duration(25)), b"\x02\x19", "sleep(duration=0.5)"),
    (WaitUntilCommand(Varuint(250)), b"\x03\xfa\x01", "wait_until(timestamp=250)"),
]


@pytest.mark.parametrize("input,output,source", COMMANDS)
def test_simple_commands(input: Node, output: bytes, source: str):
    assert input.to_bytecode() == output
    assert input.to_led_source() == source
