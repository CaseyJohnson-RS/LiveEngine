"""Снимок `ChamberRowState`: неизменяемость и производные значения."""

import dataclasses

import pytest

from engine.core.domain.enums import ChamberState
from engine.core.domain.value_objects import ChamberRowState

E, L, S = ChamberState.EMPTY, ChamberState.LOADED, ChamberState.SPENT


@pytest.mark.parametrize(
    ("outcomes", "expected"),
    [
        ((), 0),
        ((E, E), 0),
        ((L, E, L), 2),
        ((S, S, L), 1),
    ],
)
def test_remain_cartridges_counts_only_loaded(
    outcomes: tuple[ChamberState, ...], expected: int
) -> None:
    state = ChamberRowState(outcomes, (1,) * len(outcomes))
    assert state.remain_cartridges == expected


@pytest.mark.parametrize(
    "field", [f.name for f in dataclasses.fields(ChamberRowState)]
)
def test_fields_cannot_be_reassigned(field: str) -> None:
    state = ChamberRowState((E, L), (1, 2))
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(state, field, ())


def test_equal_by_value_and_hashable() -> None:
    a = ChamberRowState((E, L), (1, 2))
    b = ChamberRowState((E, L), (1, 2))
    assert a == b
    assert len({a, b}) == 1
    assert a != ChamberRowState((L, E), (1, 2))
