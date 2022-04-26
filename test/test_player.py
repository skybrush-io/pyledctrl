from pathlib import Path
from random import shuffle, seed
from typing import Tuple

from pyledctrl.player import Player

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

        expected = []
        with gzip.open(path.with_suffix(".tab.gz"), mode="rt", encoding="utf-8") as fp:  # type: ignore
            for line in fp:
                items = tuple(float(x) for x in line.split())
                expected.append((items[0], items[1:]))

        result.append((data, expected))

    return result


def almost_same_color(first: Tuple[float, ...], second: Tuple[float, ...]) -> bool:
    return len(first) == len(second) and all(
        abs(x - y) <= 1 for x, y in zip(first, second)
    )


class TestPlayer:
    test_data = load_test_data()

    @pytest.mark.parametrize("input,expected", test_data)
    def test_executor_forward(self, input, expected):
        player = Player.from_bytes(input)

        # Iterate in forward order
        for timestamp, expected_color in expected:
            color = player.get_color_at(timestamp)
            assert almost_same_color(color, expected_color)

    @pytest.mark.parametrize("input,expected", test_data)
    def test_executor_random(self, input, expected):
        player = Player.from_bytes(input)

        # Iterate in random order
        seed(42)
        shuffle(expected)
        for timestamp, expected_color in expected:
            color = player.get_color_at(timestamp)
            assert almost_same_color(color, expected_color)
