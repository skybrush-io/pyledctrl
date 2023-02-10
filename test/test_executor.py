from io import StringIO
from pathlib import Path

from pyledctrl.cli.utils import execute_and_write_tabular

import gzip
import pytest


def load_test_data():
    data_dir = Path(__file__).parent / "data" / "executor"

    result, ids = [], []

    for path in data_dir.glob("*.bin"):
        to_skip = path.name.startswith("_")
        if to_skip:
            continue

        data = path.read_bytes()

        expected = path.with_suffix(".tab").read_text()
        result.append((data, False, expected))
        ids.append(f"{path.stem}-False")

        with gzip.open(path.with_suffix(".tab.gz"), mode="rt", encoding="utf-8") as fp:
            expected = fp.read()
        result.append((data, True, expected))
        ids.append(f"{path.stem}-True")

    return result, ids


class TestExecutor:
    test_data, test_ids = load_test_data()

    @pytest.mark.parametrize("input,format,expected", test_data, ids=test_ids)
    def test_executor(self, tmp_path: Path, input, format, expected):
        (tmp_path / "input.bin").write_bytes(input)

        output = StringIO()
        execute_and_write_tabular(str(tmp_path / "input.bin"), output, unroll=format)
        result = output.getvalue().replace("\r", "")

        if expected is not None:
            assert result == expected
        else:
            assert len(result) > 0
