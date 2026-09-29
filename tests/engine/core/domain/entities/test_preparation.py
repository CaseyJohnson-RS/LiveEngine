"""Инварианты подготовки `Preparation`: фазы, участники, решения."""

from typing import cast

import pytest

from engine.core.domain.entities import Preparation
from engine.core.domain.enums import Item, PreparationPhase
from engine.core.domain.exceptions import DomainError
from engine.core.domain.exceptions.preparation import (
    PreparationArgumentError,
    PreparationDecisionError,
    PreparationError,
    PreparationPhaseError,
)
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import PreparationState, RoundConfig

A, B, C = PlayerID(1), PlayerID(2), PlayerID(3)
CONFIG = RoundConfig(chambers=4, cartridges=2, layers=(1, 1, 2))


def make_item() -> Item:
    """Уникальный предмет-заглушка: в `Item` пока нет членов."""
    return cast(Item, object())


X, Y, Z = make_item(), make_item(), make_item()


def make_preparation() -> Preparation:
    return Preparation(CONFIG, {A, B}, {A: (X, Y), B: ()})


def placing() -> Preparation:
    preparation = make_preparation()
    preparation.start_placing()
    return preparation


# --------------------------------------------------------------------------- #
# Создание
# --------------------------------------------------------------------------- #


def test_starts_in_dealing_with_no_decisions() -> None:
    preparation = make_preparation()

    assert preparation.config == CONFIG
    assert preparation.phase is PreparationPhase.DEALING
    assert preparation.participants == frozenset({A, B})
    assert preparation.confirmed == frozenset()
    assert preparation.hand(A) is None
    assert preparation.layout(A) is None


def test_offers_and_participants_are_stored_and_copied() -> None:
    offer = [X, Y]
    participants = {A}
    offers = {A: offer}
    preparation = Preparation(CONFIG, participants, offers)
    offer.append(Z)
    participants.add(B)
    offers[B] = [Z]

    assert preparation.offer(A) == (X, Y)
    assert preparation.offer(B) is None
    assert preparation.participants == frozenset({A})


def test_participant_with_empty_offer() -> None:
    preparation = make_preparation()
    assert preparation.offer(B) == ()
    assert B in preparation.participants


def test_offer_of_non_participant_is_none() -> None:
    assert make_preparation().offer(C) is None


@pytest.mark.parametrize(
    ("participants", "offers"),
    [
        (set(), {}),
        ({A, B}, {A: ()}),
        ({A}, {A: (), B: ()}),
        ({A}, {B: ()}),
    ],
    ids=[
        "no-participants",
        "participant-without-offer",
        "offer-for-non-participant",
        "offers-for-someone-else",
    ],
)
def test_participants_and_offers_mismatch_is_engine_bug(
    participants: set[PlayerID], offers: dict[PlayerID, tuple[Item, ...]]
) -> None:
    with pytest.raises(ValueError) as info:
        Preparation(CONFIG, participants, offers)
    assert not isinstance(info.value, DomainError)


def test_participants_accept_frozenset() -> None:
    preparation = Preparation(CONFIG, frozenset({A}), {A: ()})
    assert preparation.participants == frozenset({A})


# --------------------------------------------------------------------------- #
# Выдача
# --------------------------------------------------------------------------- #


def test_choose_hand_records_decision() -> None:
    preparation = make_preparation()
    preparation.choose_hand(A, [Y])

    assert preparation.hand(A) == (Y,)
    assert preparation.confirmed == frozenset({A})


def test_hand_content_is_not_checked_by_preparation() -> None:
    """Допустимость руки проверяет правило, а не подготовка."""
    preparation = make_preparation()
    preparation.choose_hand(B, [Z, Z, Z])
    assert preparation.hand(B) == (Z, Z, Z)


def test_empty_hand_allowed() -> None:
    preparation = make_preparation()
    preparation.choose_hand(A, [])
    assert preparation.hand(A) == ()


def test_hand_is_copied() -> None:
    preparation = make_preparation()
    hand = [X]
    preparation.choose_hand(A, hand)
    hand.append(Y)
    assert preparation.hand(A) == (X,)


def test_second_hand_rejected_and_unchanged() -> None:
    preparation = make_preparation()
    preparation.choose_hand(A, [X])

    with pytest.raises(PreparationDecisionError):
        preparation.choose_hand(A, [Y])
    assert preparation.hand(A) == (X,)


def test_hand_from_non_participant_rejected() -> None:
    preparation = make_preparation()
    with pytest.raises(PreparationDecisionError):
        preparation.choose_hand(C, [])
    assert preparation.confirmed == frozenset()


def test_hand_in_placing_rejected() -> None:
    preparation = placing()
    with pytest.raises(PreparationPhaseError):
        preparation.choose_hand(A, [X])
    assert preparation.hand(A) is None


def test_layout_in_dealing_rejected() -> None:
    preparation = make_preparation()
    with pytest.raises(PreparationPhaseError):
        preparation.place_chips(A, (0, 0, 0, 0))
    assert preparation.layout(A) is None


# --------------------------------------------------------------------------- #
# Смена фазы
# --------------------------------------------------------------------------- #


def test_start_placing_switches_phase_and_keeps_hands() -> None:
    preparation = make_preparation()
    preparation.choose_hand(A, [X])
    preparation.start_placing()

    assert preparation.phase is PreparationPhase.PLACING
    assert preparation.hand(A) == (X,)


def test_confirmed_follows_current_phase() -> None:
    preparation = make_preparation()
    preparation.choose_hand(A, [])
    preparation.choose_hand(B, [])
    preparation.start_placing()
    assert preparation.confirmed == frozenset()

    preparation.place_chips(B, (0, 0, 0, 0))
    assert preparation.confirmed == frozenset({B})


def test_start_placing_twice_is_engine_bug() -> None:
    preparation = placing()
    with pytest.raises(ValueError) as info:
        preparation.start_placing()
    assert not isinstance(info.value, DomainError)
    assert preparation.phase is PreparationPhase.PLACING


# --------------------------------------------------------------------------- #
# Раскладка
# --------------------------------------------------------------------------- #


def test_place_chips_records_decision() -> None:
    preparation = placing()
    preparation.place_chips(A, [1, 0, 0, 2])

    assert preparation.layout(A) == (1, 0, 0, 2)
    assert preparation.confirmed == frozenset({A})


def test_zero_layout_allowed() -> None:
    preparation = placing()
    preparation.place_chips(B, (0, 0, 0, 0))
    assert preparation.layout(B) == (0, 0, 0, 0)


def test_layout_is_copied() -> None:
    preparation = placing()
    layout = [1, 0, 0, 0]
    preparation.place_chips(A, layout)
    layout[0] = 9
    assert preparation.layout(A) == (1, 0, 0, 0)


@pytest.mark.parametrize(
    "layout",
    [(0, 0, 0), (0, 0, 0, 0, 0), ()],
    ids=["too-short", "too-long", "empty"],
)
def test_layout_of_wrong_length_rejected(layout: tuple[int, ...]) -> None:
    preparation = placing()
    with pytest.raises(PreparationArgumentError):
        preparation.place_chips(A, layout)
    assert preparation.layout(A) is None


def test_layout_with_negative_chips_rejected() -> None:
    preparation = placing()
    with pytest.raises(PreparationArgumentError):
        preparation.place_chips(A, (1, -1, 0, 0))
    assert preparation.layout(A) is None


def test_rejected_layout_does_not_count_as_decision() -> None:
    preparation = placing()
    with pytest.raises(PreparationArgumentError):
        preparation.place_chips(A, (1, -1, 0, 0))

    preparation.place_chips(A, (1, 0, 0, 0))
    assert preparation.layout(A) == (1, 0, 0, 0)


def test_second_layout_rejected_and_unchanged() -> None:
    preparation = placing()
    preparation.place_chips(A, (1, 0, 0, 0))

    with pytest.raises(PreparationDecisionError):
        preparation.place_chips(A, (0, 0, 0, 1))
    assert preparation.layout(A) == (1, 0, 0, 0)


def test_layout_from_non_participant_rejected() -> None:
    preparation = placing()
    with pytest.raises(PreparationDecisionError):
        preparation.place_chips(C, (0, 0, 0, 0))


def test_layouts_are_immutable_and_detached() -> None:
    preparation = placing()
    preparation.place_chips(A, (1, 0, 0, 0))
    layouts = preparation.layouts

    with pytest.raises(TypeError):
        layouts[B] = (9, 9, 9, 9)  # type: ignore[index]
    preparation.place_chips(B, (0, 0, 0, 0))
    assert dict(layouts) == {A: (1, 0, 0, 0)}


# --------------------------------------------------------------------------- #
# Снимок
# --------------------------------------------------------------------------- #


def test_state_reflects_everything() -> None:
    preparation = make_preparation()
    preparation.choose_hand(A, [X])
    preparation.start_placing()
    preparation.place_chips(B, (0, 0, 0, 0))

    state = preparation.state
    assert isinstance(state, PreparationState)
    assert state.config == CONFIG
    assert state.phase is PreparationPhase.PLACING
    assert dict(state.offers) == {A: (X, Y), B: ()}
    assert dict(state.hands) == {A: (X,)}
    assert dict(state.layouts) == {B: (0, 0, 0, 0)}


def test_state_is_detached_from_later_changes() -> None:
    preparation = make_preparation()
    snapshot = preparation.state
    preparation.choose_hand(A, [X])
    preparation.start_placing()

    assert snapshot.phase is PreparationPhase.DEALING
    assert dict(snapshot.hands) == {}


# --------------------------------------------------------------------------- #
# Исключения
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "error",
    [
        PreparationPhaseError,
        PreparationDecisionError,
        PreparationArgumentError,
    ],
)
def test_preparation_errors_are_domain_errors(error: type[Exception]) -> None:
    assert issubclass(error, PreparationError)
    assert issubclass(error, DomainError)
