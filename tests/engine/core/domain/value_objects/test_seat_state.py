"""Снимок `SeatState`: неизменяемость и сравнение по значению."""

import dataclasses

import pytest

from engine.core.domain.value_objects import Effect, SeatState


def make_state(**overrides: object) -> SeatState:
    fields: dict[str, object] = {
        "health_points": 3,
        "items": (),
        "effects": (),
        "chips": 1,
        "known_weight_indexes": frozenset({2}),
    }
    fields.update(overrides)
    return SeatState(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field", [f.name for f in dataclasses.fields(SeatState)]
)
def test_fields_cannot_be_reassigned(field: str) -> None:
    state = make_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(state, field, None)


def test_equal_by_value() -> None:
    effect = Effect()
    assert make_state(effects=(effect,)) == make_state(effects=(effect,))
    assert make_state(chips=1) != make_state(chips=2)


def test_hashable() -> None:
    """Все поля неизменяемы, поэтому снимок можно класть в set/dict."""
    assert len({make_state(), make_state()}) == 1
