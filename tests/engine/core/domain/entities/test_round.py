"""Инварианты раунда `Round`: свежий ряд, раскладки, раскрытые позиции.

Ряд для тестов строится без случайности: создаётся пустым
(`cartridges=0`), а нужные каморы заряжаются через `invert`.
"""

from random import Random

import pytest

from engine.core.domain.entities import ChamberRow, Round
from engine.core.domain.enums import ChamberState
from engine.core.domain.exceptions import DomainError
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import RoundState

A, B, C = PlayerID(1), PlayerID(2), PlayerID(3)
E, L, S = ChamberState.EMPTY, ChamberState.LOADED, ChamberState.SPENT


def make_row(pattern: str) -> ChamberRow:
    """Свежий ряд по шаблону: `.` — пустая камора, `x` — заряженная."""
    row = ChamberRow([1] * len(pattern), 0, Random(0))
    for i, c in enumerate(pattern):
        if c == "x":
            row.invert(i)
    return row


def make_round(
    pattern: str = "x..x",
    layouts: dict[PlayerID, tuple[int, ...]] | None = None,
) -> Round:
    row = make_row(pattern)
    if layouts is None:
        layouts = {A: (1, 0, 0, 2), B: (0, 0, 0, 0)}
    return Round(row, layouts, pattern.count("x"))


# --------------------------------------------------------------------------- #
# Создание
# --------------------------------------------------------------------------- #


def test_stores_row_cartridges_and_layouts() -> None:
    row = make_row("x..x")
    round_ = Round(row, {A: (1, 0, 0, 2)}, 2)

    assert round_.row is row
    assert round_.initial_cartridges == 2
    assert round_.layout(A) == (1, 0, 0, 2)


def test_player_without_layout_has_none() -> None:
    assert make_round().layout(C) is None


def test_empty_layouts_allowed() -> None:
    round_ = make_round(layouts={})
    assert round_.layout(A) is None


def test_zero_chip_layout_allowed() -> None:
    round_ = make_round(layouts={A: (0, 0, 0, 0)})
    assert round_.layout(A) == (0, 0, 0, 0)


def test_layouts_are_copied_into_tuples() -> None:
    layout = [1, 0, 0, 2]
    layouts = {A: layout}
    round_ = Round(make_row("x..x"), layouts, 2)
    layout[0] = 9
    layouts[B] = [0, 0, 0, 0]

    assert round_.layout(A) == (1, 0, 0, 2)
    assert round_.layout(B) is None


@pytest.mark.parametrize("pattern", ["....", "xxxx", "x.x."])
def test_initial_cartridges_matching_the_row_accepted(pattern: str) -> None:
    round_ = make_round(pattern, layouts={})
    assert round_.initial_cartridges == pattern.count("x")


@pytest.mark.parametrize("initial", [0, 1, 3, 5])
def test_initial_cartridges_not_matching_the_row_rejected(
    initial: int,
) -> None:
    with pytest.raises(ValueError):
        Round(make_row("x..x"), {}, initial)


def test_row_with_spent_chamber_rejected() -> None:
    row = make_row("x..x")
    row.spend(1)

    with pytest.raises(ValueError):
        Round(row, {}, 2)


@pytest.mark.parametrize(
    "layout",
    [(1, 0, 0), (1, 0, 0, 0, 0), ()],
    ids=["too-short", "too-long", "empty"],
)
def test_layout_of_wrong_length_rejected(layout: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        make_round(layouts={A: (0, 0, 0, 0), B: layout})


def test_layout_with_negative_chips_rejected() -> None:
    with pytest.raises(ValueError):
        make_round(layouts={A: (1, -1, 0, 0)})


def test_errors_are_not_domain_errors() -> None:
    """Нарушить инварианты раунда может только баг в правиле."""
    with pytest.raises(ValueError) as info:
        make_round(layouts={A: (1, -1, 0, 0)})
    assert not isinstance(info.value, DomainError)


# --------------------------------------------------------------------------- #
# Раскрытые позиции
# --------------------------------------------------------------------------- #


def test_nothing_revealed_by_default() -> None:
    round_ = make_round()
    assert round_.revealed(A) == frozenset()
    assert round_.revealed(C) == frozenset()


def test_reveal_adds_position() -> None:
    round_ = make_round()
    round_.reveal(A, 2)
    round_.reveal(A, 0)
    assert round_.revealed(A) == frozenset({0, 2})


def test_reveal_twice_is_noop() -> None:
    round_ = make_round()
    round_.reveal(A, 2)
    round_.reveal(A, 2)
    assert round_.revealed(A) == frozenset({2})


def test_revealed_positions_are_per_player() -> None:
    round_ = make_round()
    round_.reveal(A, 1)
    round_.reveal(B, 3)

    assert round_.revealed(A) == frozenset({1})
    assert round_.revealed(B) == frozenset({3})


def test_reveal_to_player_without_layout_allowed() -> None:
    round_ = make_round()
    round_.reveal(C, 0)
    assert round_.revealed(C) == frozenset({0})


def test_reveal_spent_chamber_allowed() -> None:
    round_ = make_round()
    round_.row.spend(0)
    round_.reveal(A, 0)
    assert round_.revealed(A) == frozenset({0})


@pytest.mark.parametrize("position", [-1, 4, 100])
def test_reveal_outside_row_rejected_and_unchanged(position: int) -> None:
    round_ = make_round()
    round_.reveal(A, 1)

    with pytest.raises(ValueError):
        round_.reveal(A, position)
    assert round_.revealed(A) == frozenset({1})


# --------------------------------------------------------------------------- #
# Ряд меняется, данные зарядки — нет
# --------------------------------------------------------------------------- #


def test_row_changes_do_not_touch_loading_data() -> None:
    round_ = make_round()
    round_.row.spend(0)
    round_.row.invert(1)

    assert round_.initial_cartridges == 2
    assert round_.layout(A) == (1, 0, 0, 2)
    assert round_.state.row.outcomes == (S, L, E, L)


# --------------------------------------------------------------------------- #
# Снимок
# --------------------------------------------------------------------------- #


def test_state_reflects_everything() -> None:
    round_ = make_round()
    round_.reveal(A, 3)

    state = round_.state
    assert isinstance(state, RoundState)
    assert state.row == round_.row.state
    assert state.initial_cartridges == 2
    assert dict(state.layouts) == {A: (1, 0, 0, 2), B: (0, 0, 0, 0)}
    assert dict(state.revealed) == {A: frozenset({3})}


def test_state_is_detached_from_later_changes() -> None:
    round_ = make_round()
    snapshot = round_.state
    round_.reveal(A, 1)
    round_.row.spend(0)

    assert dict(snapshot.revealed) == {}
    assert snapshot.row.outcomes == (L, E, E, L)
