import json
import pickle
import pytest

from functools import partial
from pathlib import Path

from pyledctrl.compiler import BytecodeCompiler
from pyledctrl.compiler.formats import OutputFormat
from pyledctrl.compiler.plan import Plan
from pyledctrl.compiler.stages import ConstantOutputStage, DummyStage


def load_led_test_data():
    data_dir = Path(__file__).parent / "data" / "compiler"

    result, ids = [], []

    for path in data_dir.glob("*.led"):
        to_skip = path.name.startswith("_")
        data = path.read_bytes()
        for format in (
            OutputFormat.LEDCTRL_BINARY,
            OutputFormat.LEDCTRL_JSON,
            OutputFormat.LEDCTRL_SOURCE,
        ):
            if to_skip:
                result.append(pytest.param(data, format, None, marks=pytest.mark.xfail))
            else:
                if format is OutputFormat.LEDCTRL_BINARY:
                    expected = path.with_suffix(".bin").read_bytes()
                elif format is OutputFormat.LEDCTRL_SOURCE:
                    expected = path.with_suffix(".oled").read_bytes()
                elif format is OutputFormat.LEDCTRL_JSON:
                    expected = json.loads(path.with_suffix(".json").read_text())
                else:
                    expected = None
                result.append((data, format, expected))
            ids.append(f"{path.stem} to {format.value}")

    return result, ids


class TestCompilationFromLEDFile:
    test_data, test_ids = load_led_test_data()

    @pytest.mark.parametrize("input,format,expected", test_data, ids=test_ids)
    def test_compilation(self, tmp_path: Path, input, format, expected):
        compiler = BytecodeCompiler(optimisation_level=2)

        (tmp_path / "input.led").write_bytes(input)
        compiler.compile(
            tmp_path / "input.led", str(tmp_path / "out"), output_format=format
        )

        if format is OutputFormat.LEDCTRL_JSON:
            with (tmp_path / "out").open() as fp:
                result = json.load(fp)
        else:
            result = (tmp_path / "out").read_bytes()

        if expected is not None:
            assert result == expected
        else:
            assert len(result) > 0


def load_ast_test_data():
    data_dir = Path(__file__).parent / "data" / "compiler"

    result, ids = [], []

    for path in data_dir.glob("*.ast"):
        to_skip = path.name.startswith("_")
        with path.open("rb") as fp:
            data = pickle.load(fp)
        for format in (
            OutputFormat.LEDCTRL_BINARY,
            OutputFormat.LEDCTRL_JSON,
            OutputFormat.LEDCTRL_SOURCE,
        ):
            if to_skip:
                result.append(pytest.param(data, format, None, marks=pytest.mark.xfail))
            else:
                if format is OutputFormat.LEDCTRL_BINARY:
                    expected = path.with_suffix(".bin").read_bytes()
                elif format is OutputFormat.LEDCTRL_SOURCE:
                    expected = path.with_suffix(".oled").read_bytes()
                elif format is OutputFormat.LEDCTRL_JSON:
                    expected = json.loads(path.with_suffix(".json").read_text())
                else:
                    expected = None
                result.append((data, format, expected))
            ids.append(f"{path.stem} to {format.value}")

    return result, ids


class TestCompilationFromASTObject:
    test_data, test_ids = load_ast_test_data()

    @pytest.mark.parametrize("input,format,expected", test_data, ids=test_ids)
    def test_compilation(self, tmp_path: Path, input, format, expected):
        compiler = BytecodeCompiler(optimisation_level=2)

        compiler.compile(input, str(tmp_path / "out"), output_format=format)

        if format is OutputFormat.LEDCTRL_JSON:
            with (tmp_path / "out").open() as fp:
                result = json.load(fp)
        else:
            result = (tmp_path / "out").read_bytes()

        if expected is not None:
            assert result == expected
        else:
            assert len(result) > 0


def test_callbacks_in_steps():
    value_holder = []

    def set_done(holder, default_output="OK", output=None):
        holder.append(output or default_output)

    plan = Plan()
    plan.add_step(DummyStage()).and_when_done(set_done, value_holder)

    plan.execute()
    assert value_holder == ["OK"]

    new_stage = DummyStage()
    plan.add_step(new_stage)
    decorator = plan.when_step_is_done(new_stage)
    decorator(partial(set_done, value_holder, "OK 2"))

    value_holder.clear()
    plan.execute()
    assert value_holder == ["OK", "OK 2"]

    output_stage = ConstantOutputStage(42)
    plan.add_step(output_stage).mark_as_output()
    plan.when_step_is_done(output_stage, partial(set_done, value_holder, "OK 3"))

    value_holder.clear()
    plan.execute()
    assert value_holder == ["OK", "OK 2", 42]


def test_iter_steps_in_plan():
    plan = Plan()

    stage1 = DummyStage()
    stage2 = DummyStage()
    stage3 = ConstantOutputStage(42)

    plan.add_step(stage2)
    plan.insert_step(stage1, before=stage2)
    plan.insert_step(stage3, after=stage2)

    assert list(plan.iter_steps()) == [stage1, stage2, stage3]
