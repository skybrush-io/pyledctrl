from pathlib import Path

from pyledctrl.compiler import BytecodeCompiler
from pyledctrl.compiler.formats import OutputFormat

import pytest


def load_test_data():
    data_dir = Path(__file__).parent / "data"

    result = []

    for path in data_dir.glob("*.led"):
        to_skip = path.name.startswith("_")
        data = path.read_bytes()
        for format in (
            OutputFormat.LEDCTRL_BINARY,
            OutputFormat.LEDCTRL_JSON,
            OutputFormat.LEDCTRL_SOURCE,
        ):
            if to_skip:
                result.append(pytest.param(data, format, marks=pytest.mark.xfail))
            else:
                result.append((data, format))

    return result


class TestCompilation:
    test_data = load_test_data()

    @pytest.mark.parametrize("input,format", test_data)
    def test_compilation(self, tmp_path: Path, input, format):
        compiler = BytecodeCompiler(optimisation_level=2)

        (tmp_path / "input.led").write_bytes(input)
        compiler.compile(
            tmp_path / "input.led", str(tmp_path / "out"), output_format=format
        )
        result = (tmp_path / "out").read_bytes()

        assert len(result) > 0
