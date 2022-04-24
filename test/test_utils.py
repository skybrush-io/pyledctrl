from pytest import mark, raises

from pyledctrl.utils import (
    consecutive_pairs,
    ensure_tuple,
    first,
    format_frame_count,
    last,
    parse_as_frame_count,
)


def test_consecutive_pairs():
    assert list(consecutive_pairs([1, 2, 3, 4])) == [(1, 2), (2, 3), (3, 4)]
    assert list(consecutive_pairs([])) == []
    assert list(consecutive_pairs([1])) == []


@mark.parametrize("input", [True, "foo", (), ("foobar",), (1, 2, 3)])
def test_ensure_tuple(input):
    if isinstance(input, tuple):
        assert ensure_tuple(input) is input
    else:
        assert ensure_tuple(input) == (input,)


def test_first():
    assert first([1, 2, 3]) == 1
    assert first(iter((4, 5, 6))) == 4
    with raises(ValueError, match="iterable is empty"):
        first(())


def test_last():
    assert last([1, 2, 3]) == 3
    assert last(iter((4, 5, 6))) == 6
    with raises(ValueError, match="iterable is empty"):
        last(())


FRAME_COUNT_TESTS = [
    (0, "0:00+00"),
    (12, "0:00+12"),
    (24, "0:01+00"),
    (54, "0:02+06"),
    (1494, "1:02+06"),
]


@mark.parametrize("input,output", FRAME_COUNT_TESTS)
def test_format_frame_count(input, output):
    assert format_frame_count(input, fps=24) == output


@mark.parametrize("output,input", FRAME_COUNT_TESTS)
def test_parse_frame_count(input, output):
    assert parse_as_frame_count(input, fps=24) == output
