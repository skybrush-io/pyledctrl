from pathlib import Path

from pyledctrl.app import dump

import gzip
import pytest


def load_test_data():
    data_dir = Path(__file__).parent / "data" / "executor"

    result = []

    for path in data_dir.glob("*.bin"):
        to_skip = path.name.startswith("_")
        if to_skip:
            continue

        data = path.read_bytes()

        expected = path.with_suffix(".tab").read_text()
        result.append((data, False, expected))

        with gzip.open(path.with_suffix(".tab.gz"), mode="rt", encoding="utf-8") as fp:
            expected = fp.read()
        result.append((data, True, expected))

    return result


class TestExecutor:
    test_data = load_test_data()

    @pytest.mark.parametrize("input,format,expected", test_data)
    def test_executor(self, tmp_path: Path, input, format, expected):
        (tmp_path / "input.bin").write_bytes(input)
        args = ["-o", str(tmp_path / "output.tab"), str(tmp_path / "input.bin")]
        if format:
            args.insert(0, "--unroll")

        dump(args, standalone_mode=False)

        result = (tmp_path / "output.tab").read_text().replace("\r", "")

        if expected is not None:
            assert result == expected
        else:
            assert len(result) > 0
