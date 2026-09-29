"""Поведение каморного ряда `ChamberRow`.

Раскладка для детерминированных тестов строится без случайности:
ряд создаётся пустым (`cartridges=0`) или полностью заряженным
(`cartridges=n`), а нужные каморы затем переключаются через `invert`.
"""

import math
from collections import Counter
from itertools import combinations
from random import Random

import pytest

from engine.core.domain.entities import ChamberRow
from engine.core.domain.entities.chamber_row._limits import (
    MAX_SIZE,
    MAX_WEIGHT,
)
from engine.core.domain.enums import ChamberState
from engine.core.domain.exceptions import DomainError
from engine.core.domain.exceptions.chamber_row import (
    ChamberPositionError,
    ChamberRowError,
    ChamberSpentError,
    ChamberUnavailableError,
)
from engine.libs.weighted_subset_sampler import _limits as sampler_limits

E, L, S = ChamberState.EMPTY, ChamberState.LOADED, ChamberState.SPENT

TRIALS = 20_000
SIGMAS = 5.0


def make_row(pattern: str, weights: list[int] | None = None) -> ChamberRow:
    """Ряд по шаблону: `.` — пустая, `x` — заряженная, `s` — отстрелянная.

    Отстрелянные получаются тратой пустых камор, поэтому исход раскладки
    не зависит от сида.
    """
    n = len(pattern)
    row = ChamberRow(weights or [1] * n, 0, Random(0))
    for i, c in enumerate(pattern):
        if c == "x":
            row.invert(i)
        elif c == "s":
            row.spend(i)
    return row


def outcomes(row: ChamberRow) -> tuple[ChamberState, ...]:
    return row.state.outcomes


def within(observed: int, p: float, trials: int = TRIALS) -> bool:
    sigma = math.sqrt(trials * p * (1 - p))
    return abs(observed - trials * p) <= SIGMAS * sigma


def subset_probabilities(
    weights: list[float], k: int
) -> dict[tuple[int, ...], float]:
    products = {
        s: math.prod(weights[i] for i in s)
        for s in combinations(range(len(weights)), k)
    }
    total = sum(products.values())
    return {s: p / total for s, p in products.items()}


# --------------------------------------------------------------------------- #
# Пределы
# --------------------------------------------------------------------------- #


def test_limits_fit_into_sampler_limits() -> None:
    """Ряд передаёт сэмплеру веса и обратные им; оба должны пройти."""
    assert MAX_SIZE <= sampler_limits.MAX_SIZE
    assert MAX_WEIGHT <= sampler_limits.MAX_WEIGHT


# --------------------------------------------------------------------------- #
# Создание
# --------------------------------------------------------------------------- #


def test_zero_cartridges_gives_empty_row() -> None:
    row = ChamberRow([1, 2, 3], 0, Random(0))
    assert outcomes(row) == (E, E, E)
    assert row.size == 3
    assert not row.is_exhausted


def test_full_cartridges_gives_loaded_row() -> None:
    row = ChamberRow([1, 2, 3], 3, Random(0))
    assert outcomes(row) == (L, L, L)


@pytest.mark.parametrize("cartridges", range(6))
def test_initial_placement_has_exact_count_and_no_spent(
    cartridges: int,
) -> None:
    rng = Random(cartridges)
    for _ in range(50):
        row = ChamberRow([1, 5, 2, 9, 3], cartridges, rng)
        assert row.state.remain_cartridges == cartridges
        assert S not in outcomes(row)


def test_weights_are_copied() -> None:
    weights = [1, 2, 3]
    row = ChamberRow(weights, 1, Random(0))
    weights[0] = 50

    assert row.state.weights == (1, 2, 3)


def test_same_seed_same_placement() -> None:
    a = ChamberRow([1, 7, 3, 2, 9, 4], 3, Random(11))
    b = ChamberRow([1, 7, 3, 2, 9, 4], 3, Random(11))
    assert outcomes(a) == outcomes(b)


def test_initial_placement_follows_weights() -> None:
    """Вероятность набора заряженных камор ∝ произведению их весов."""
    weights = [1, 2, 5, 10]
    exact = subset_probabilities([float(w) for w in weights], 2)
    rng = Random(1)
    counts = Counter(
        tuple(
            i
            for i, s in enumerate(outcomes(ChamberRow(weights, 2, rng)))
            if s is L
        )
        for _ in range(TRIALS)
    )
    for subset, p in exact.items():
        assert within(counts[subset], p), subset


@pytest.mark.parametrize(
    ("weights", "cartridges"),
    [
        ([], 0),
        ([1] * (MAX_SIZE + 1), 0),
        ([1, 0, 1], 1),
        ([1, MAX_WEIGHT + 1], 1),
        ([1, -3], 0),
        ([1, 1, 1], -1),
        ([1, 1, 1], 4),
    ],
    ids=[
        "empty",
        "too-long",
        "zero-weight",
        "weight-over-max",
        "negative-weight",
        "negative-cartridges",
        "too-many-cartridges",
    ],
)
def test_bad_parameters_raise_value_error(
    weights: list[int], cartridges: int
) -> None:
    with pytest.raises(ValueError) as info:
        ChamberRow(weights, cartridges, Random(0))
    assert not isinstance(info.value, DomainError)


def test_boundary_parameters_accepted() -> None:
    ChamberRow([1] * MAX_SIZE, MAX_SIZE, Random(0))
    ChamberRow([1, MAX_WEIGHT], 0, Random(0))


# --------------------------------------------------------------------------- #
# spend
# --------------------------------------------------------------------------- #


def test_spend_loaded_returns_true() -> None:
    row = make_row(".x.")
    assert row.spend(1) is True
    assert outcomes(row) == (E, S, E)


def test_spend_empty_returns_false() -> None:
    row = make_row(".x.")
    assert row.spend(0) is False
    assert outcomes(row) == (S, L, E)


def test_spend_spent_rejected_and_unchanged() -> None:
    row = make_row("sx.")
    with pytest.raises(ChamberSpentError):
        row.spend(0)
    assert outcomes(row) == (S, L, E)


@pytest.mark.parametrize("position", [-1, 3, 100])
def test_spend_outside_row_rejected(position: int) -> None:
    row = make_row(".x.")
    with pytest.raises(ChamberPositionError):
        row.spend(position)
    assert outcomes(row) == (E, L, E)


# --------------------------------------------------------------------------- #
# invert
# --------------------------------------------------------------------------- #


def test_invert_toggles_both_ways() -> None:
    row = make_row("..")
    row.invert(0)
    assert outcomes(row) == (L, E)
    row.invert(0)
    assert outcomes(row) == (E, E)


def test_invert_changes_cartridge_count() -> None:
    row = make_row("x.")
    row.invert(1)
    assert row.state.remain_cartridges == 2


def test_invert_spent_rejected_and_unchanged() -> None:
    row = make_row("s.")
    with pytest.raises(ChamberSpentError):
        row.invert(0)
    assert outcomes(row) == (S, E)


@pytest.mark.parametrize("position", [-1, 2])
def test_invert_outside_row_rejected(position: int) -> None:
    row = make_row("..")
    with pytest.raises(ChamberPositionError):
        row.invert(position)


# --------------------------------------------------------------------------- #
# is_exhausted
# --------------------------------------------------------------------------- #


def test_exhausted_only_when_every_chamber_spent() -> None:
    row = make_row("x..")
    for position in range(row.size - 1):
        row.spend(position)
        assert not row.is_exhausted
    row.spend(row.size - 1)
    assert row.is_exhausted


# --------------------------------------------------------------------------- #
# add_cartridge
# --------------------------------------------------------------------------- #


def test_add_loads_exactly_one_empty_chamber() -> None:
    rng = Random(3)
    for _ in range(200):
        row = make_row("x.s..s")
        before = outcomes(row)
        row.add_cartridge(rng)
        after = outcomes(row)

        changed = [i for i in range(row.size) if before[i] != after[i]]
        assert len(changed) == 1
        assert before[changed[0]] is E
        assert after[changed[0]] is L


def test_add_uses_the_only_empty_chamber() -> None:
    row = make_row("xs.s")
    row.add_cartridge(Random(0))
    assert outcomes(row) == (L, S, L, S)


@pytest.mark.parametrize("pattern", ["xx", "sx", "ss"])
def test_add_without_empty_chamber_rejected(pattern: str) -> None:
    row = make_row(pattern)
    before = outcomes(row)
    with pytest.raises(ChamberUnavailableError):
        row.add_cartridge(Random(0))
    assert outcomes(row) == before


def test_add_is_proportional_to_weight() -> None:
    weights = [1, 2, 3, 4]
    total = sum(weights)
    rng = Random(5)
    counts: Counter[int] = Counter()
    for _ in range(TRIALS):
        row = make_row("....", weights)
        row.add_cartridge(rng)
        counts[outcomes(row).index(L)] += 1

    for i, w in enumerate(weights):
        assert within(counts[i], w / total), i


# --------------------------------------------------------------------------- #
# remove_cartridge
# --------------------------------------------------------------------------- #


def test_remove_unloads_exactly_one_loaded_chamber() -> None:
    rng = Random(4)
    for _ in range(200):
        row = make_row("x.sxxs")
        before = outcomes(row)
        row.remove_cartridge(rng)
        after = outcomes(row)

        changed = [i for i in range(row.size) if before[i] != after[i]]
        assert len(changed) == 1
        assert before[changed[0]] is L
        assert after[changed[0]] is E


def test_remove_uses_the_only_loaded_chamber() -> None:
    row = make_row(".sx.")
    row.remove_cartridge(Random(0))
    assert outcomes(row) == (E, S, E, E)


@pytest.mark.parametrize("pattern", ["..", "s.", "ss"])
def test_remove_without_loaded_chamber_rejected(pattern: str) -> None:
    row = make_row(pattern)
    before = outcomes(row)
    with pytest.raises(ChamberUnavailableError):
        row.remove_cartridge(Random(0))
    assert outcomes(row) == before


def test_remove_is_inversely_proportional_to_weight() -> None:
    weights = [1, 2, 4, 8]
    inverse_total = sum(1 / w for w in weights)
    rng = Random(6)
    counts: Counter[int] = Counter()
    for _ in range(TRIALS):
        row = make_row("xxxx", weights)
        row.remove_cartridge(rng)
        counts[outcomes(row).index(E)] += 1

    for i, w in enumerate(weights):
        assert within(counts[i], (1 / w) / inverse_total), i


# --------------------------------------------------------------------------- #
# shake
# --------------------------------------------------------------------------- #


def test_shake_keeps_count_and_spent_positions() -> None:
    rng = Random(7)
    row = make_row("sx.xs..x", [3, 1, 4, 1, 5, 9, 2, 6])
    for _ in range(200):
        row.shake(rng)
        state = outcomes(row)
        assert row.state.remain_cartridges == 3
        assert [i for i, s in enumerate(state) if s is S] == [0, 4]


@pytest.mark.parametrize("pattern", ["s..", "...", "sxx", "xxx"])
def test_shake_without_choice_is_allowed_and_changes_nothing(
    pattern: str,
) -> None:
    """Все неотстрелянные пусты или все заряжены: встряхнуть можно."""
    row = make_row(pattern)
    before = outcomes(row)
    row.shake(Random(0))
    assert outcomes(row) == before


def test_shake_all_spent_rejected() -> None:
    row = make_row("ss")
    with pytest.raises(ChamberUnavailableError):
        row.shake(Random(0))
    assert outcomes(row) == (S, S)


def test_shake_follows_weights_of_unspent() -> None:
    """После встряски набор патронов распределён по весам неотстрелянных."""
    weights = [7, 2, 3, 4, 5]
    row = make_row("sxx..", weights)
    unspent = [1, 2, 3, 4]
    exact = subset_probabilities([float(weights[i]) for i in unspent], 2)
    rng = Random(8)
    counts: Counter[tuple[int, ...]] = Counter()
    for _ in range(TRIALS):
        row.shake(rng)
        state = outcomes(row)
        counts[tuple(j for j, i in enumerate(unspent) if state[i] is L)] += 1

    for subset, p in exact.items():
        assert within(counts[subset], p), subset


# --------------------------------------------------------------------------- #
# Детерминизм и снимок
# --------------------------------------------------------------------------- #


def test_same_seed_same_history() -> None:
    def play(seed: int) -> list[tuple[ChamberState, ...]]:
        rng = Random(seed)
        row = ChamberRow([2, 7, 1, 8, 2, 8], 2, rng)
        history = [outcomes(row)]
        row.spend(0)
        for step in (row.add_cartridge, row.shake, row.remove_cartridge):
            step(rng)
            history.append(outcomes(row))
        return history

    assert play(42) == play(42)


def test_state_is_detached_from_later_changes() -> None:
    row = make_row("x.")
    snapshot = row.state
    row.spend(0)

    assert snapshot.outcomes == (L, E)
    assert snapshot.remain_cartridges == 1


# --------------------------------------------------------------------------- #
# Атрибуты
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["outcomes", "weight", "rng"])
def test_unknown_attribute_cannot_be_set(name: str) -> None:
    """Опечатка в имени атрибута падает сразу, а не создаёт новое поле."""
    row = make_row("..")
    with pytest.raises(AttributeError):
        setattr(row, name, 1)


# --------------------------------------------------------------------------- #
# Исключения
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "error",
    [ChamberPositionError, ChamberSpentError, ChamberUnavailableError],
)
def test_row_errors_are_domain_errors(error: type[Exception]) -> None:
    assert issubclass(error, ChamberRowError)
    assert issubclass(error, DomainError)
