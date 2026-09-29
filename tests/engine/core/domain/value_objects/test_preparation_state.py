"""Снимок `PreparationState`: неизменяемость и сравнение по значению."""

import dataclasses

import pytest

from engine.core.domain.enums import PreparationPhase
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import PreparationState, RoundConfig

A = PlayerID(1)


def make_state(**overrides: object) -> PreparationState:
    fields: dict[str, object] = {
        "config": RoundConfig(chambers=2, cartridges=1, layers=(1,)),
        "phase": PreparationPhase.DEALING,
        "offers": frozendict({A: ()}),  # type: ignore
        "hands": frozendict(),  # type: ignore
        "layouts": frozendict(),  # type: ignore
    }
    fields.update(overrides)
    return PreparationState(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field", [f.name for f in dataclasses.fields(PreparationState)]
)
def test_fields_cannot_be_reassigned(field: str) -> None:
    state = make_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(state, field, None)


def test_equal_by_value_and_hashable() -> None:
    assert make_state() == make_state()
    assert len({make_state(), make_state()}) == 1
    assert make_state(phase=PreparationPhase.PLACING) != make_state()
