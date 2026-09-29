"""Снимок `RoundState`: неизменяемость и сравнение по значению."""

import dataclasses

import pytest

from engine.core.domain.enums import ChamberState
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import ChamberRowState, RoundState

A = PlayerID(1)
E, L = ChamberState.EMPTY, ChamberState.LOADED


def make_state(**overrides: object) -> RoundState:
    fields: dict[str, object] = {
        "row": ChamberRowState((E, L), (1, 2)),
        "initial_cartridges": 1,
        "layouts": frozendict({A: (0, 1)}),  # type: ignore
        "revealed": frozendict({A: frozenset({1})}),  # type: ignore
    }
    fields.update(overrides)
    return RoundState(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field", [f.name for f in dataclasses.fields(RoundState)]
)
def test_fields_cannot_be_reassigned(field: str) -> None:
    state = make_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(state, field, None)


def test_mappings_cannot_be_modified() -> None:
    state = make_state()
    with pytest.raises(TypeError):
        state.layouts[A] = (1, 1)  # type: ignore[index]


def test_equal_by_value_and_hashable() -> None:
    assert make_state() == make_state()
    assert len({make_state(), make_state()}) == 1
    assert make_state(initial_cartridges=2) != make_state()
