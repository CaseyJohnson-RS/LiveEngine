"""Инварианты места `Seat`: диапазоны значений и заморозка выбывшего."""

from collections.abc import Callable
from typing import cast

import pytest

from engine.core.domain.entities import Seat
from engine.core.domain.enums import Item
from engine.core.domain.exceptions import DomainError
from engine.core.domain.exceptions.seat import (
    SeatArgumentError,
    SeatError,
    SeatStateError,
)
from engine.core.domain.value_objects import Effect, SeatState

MAX_ITEMS = 3
MAX_HP = 4


def make_item() -> Item:
    """Уникальный предмет-заглушка: в `Item` пока нет членов."""
    return cast(Item, object())


def alive_seat() -> Seat:
    return Seat(max_items=MAX_ITEMS, health_points=MAX_HP)


def dead_seat() -> Seat:
    seat = alive_seat()
    seat.health_points = 0
    return seat


# --------------------------------------------------------------------------- #
# Создание
# --------------------------------------------------------------------------- #


def test_new_seat_has_full_health_and_nothing_else() -> None:
    seat = alive_seat()

    assert seat.is_alive
    assert seat.health_points == MAX_HP
    assert seat.items == ()
    assert seat.effects == ()
    assert seat.chips == 0


@pytest.mark.parametrize("health_points", [0, -1])
def test_non_positive_health_rejected(health_points: int) -> None:
    with pytest.raises(SeatArgumentError):
        Seat(max_items=MAX_ITEMS, health_points=health_points)


def test_negative_max_items_rejected() -> None:
    with pytest.raises(SeatArgumentError):
        Seat(max_items=-1, health_points=MAX_HP)


def test_zero_max_items_allowed_but_holds_nothing() -> None:
    seat = Seat(max_items=0, health_points=MAX_HP)
    seat.items = []

    with pytest.raises(SeatArgumentError):
        seat.items = [make_item()]


# --------------------------------------------------------------------------- #
# Здоровье
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("value", [1, MAX_HP // 2, MAX_HP])
def test_health_can_be_set_within_range(value: int) -> None:
    seat = alive_seat()
    seat.health_points = value
    assert seat.health_points == value
    assert seat.is_alive


@pytest.mark.parametrize("value", [-1, MAX_HP + 1])
def test_health_out_of_range_rejected_and_unchanged(value: int) -> None:
    seat = alive_seat()
    seat.health_points = 2

    with pytest.raises(SeatArgumentError):
        seat.health_points = value
    assert seat.health_points == 2


def test_setting_zero_health_kills() -> None:
    seat = alive_seat()
    seat.health_points = 0

    assert not seat.is_alive
    assert seat.health_points == 0


# --------------------------------------------------------------------------- #
# Заморозка выбывшего места
# --------------------------------------------------------------------------- #

FROZEN_SETTERS: dict[str, Callable[[Seat], None]] = {
    "resurrect": lambda seat: setattr(seat, "health_points", MAX_HP),
    "health-zero-again": lambda seat: setattr(seat, "health_points", 0),
    "effects": lambda seat: setattr(seat, "effects", [Effect()]),
    "clear-effects": lambda seat: setattr(seat, "effects", []),
    "chips": lambda seat: setattr(seat, "chips", 1),
    "chips-zero": lambda seat: setattr(seat, "chips", 0),
}


@pytest.mark.parametrize(
    "mutate", FROZEN_SETTERS.values(), ids=FROZEN_SETTERS.keys()
)
def test_dead_seat_is_frozen(mutate: Callable[[Seat], None]) -> None:
    seat = dead_seat()
    before = seat.state

    with pytest.raises(SeatStateError):
        mutate(seat)
    assert seat.state == before


def test_dead_seat_items_stay_mutable() -> None:
    """Предметы выбывшего могут забрать другие места."""
    seat = alive_seat()
    item = make_item()
    seat.items = [item]
    seat.health_points = 0

    seat.items = []
    assert seat.items == ()


# --------------------------------------------------------------------------- #
# Предметы
# --------------------------------------------------------------------------- #


def test_items_up_to_limit_accepted_in_order() -> None:
    seat = alive_seat()
    items = [make_item() for _ in range(MAX_ITEMS)]
    seat.items = items

    assert seat.items == tuple(items)


def test_items_over_limit_rejected_and_unchanged() -> None:
    seat = alive_seat()
    kept = [make_item()]
    seat.items = kept

    with pytest.raises(SeatArgumentError):
        seat.items = [make_item() for _ in range(MAX_ITEMS + 1)]
    assert seat.items == tuple(kept)


def test_items_are_copied_on_set() -> None:
    seat = alive_seat()
    items = [make_item()]
    seat.items = items
    items.append(make_item())

    assert len(seat.items) == 1


def test_duplicate_items_allowed() -> None:
    seat = alive_seat()
    item = make_item()
    seat.items = [item, item]
    assert seat.items == (item, item)


# --------------------------------------------------------------------------- #
# Эффекты
# --------------------------------------------------------------------------- #


def test_effects_set_and_copied() -> None:
    seat = alive_seat()
    effects = [Effect(), Effect()]
    seat.effects = effects
    effects.clear()

    assert len(seat.effects) == 2


# --------------------------------------------------------------------------- #
# Фишки
# --------------------------------------------------------------------------- #


def test_chips_can_be_incremented_in_place() -> None:
    seat = alive_seat()
    seat.chips += 1
    seat.chips += 2
    assert seat.chips == 3


def test_negative_chips_rejected_and_unchanged() -> None:
    seat = alive_seat()
    seat.chips = 1

    with pytest.raises(SeatArgumentError):
        seat.chips -= 2
    assert seat.chips == 1


# --------------------------------------------------------------------------- #
# Снимок
# --------------------------------------------------------------------------- #


def test_state_reflects_current_values() -> None:
    seat = alive_seat()
    item, effect = make_item(), Effect()
    seat.health_points = 2
    seat.items = [item]
    seat.effects = [effect]
    seat.chips = 5

    assert seat.state == SeatState(
        health_points=2,
        items=(item,),
        effects=(effect,),
        chips=5,
    )


def test_state_is_detached_from_later_changes() -> None:
    seat = alive_seat()
    snapshot = seat.state
    seat.chips = 7
    seat.items = [make_item()]

    assert snapshot.chips == 0
    assert snapshot.items == ()


# --------------------------------------------------------------------------- #
# Атрибуты
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["chip", "known_weight_indexes", "hp"])
def test_unknown_attribute_cannot_be_set(name: str) -> None:
    """Опечатка в имени атрибута падает сразу, а не создаёт новое поле."""
    seat = alive_seat()
    with pytest.raises(AttributeError):
        setattr(seat, name, 1)


# --------------------------------------------------------------------------- #
# Исключения
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("error", [SeatStateError, SeatArgumentError])
def test_seat_errors_are_domain_errors(error: type[Exception]) -> None:
    assert issubclass(error, SeatError)
    assert issubclass(error, DomainError)
