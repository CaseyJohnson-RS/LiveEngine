"""Контракт публичного интерфейса: форма результата, детерминизм, граничные k."""

import itertools
from random import Random

import pytest

from libs.weighted_subset_sampler import sample_weighted_mask, sample_weighted_subset

WEIGHTS_CASES = [
    [1.0],
    [1.0, 1.0],
    [1.0, 2.0, 3.0, 4.0, 5.0],
    [0.5, 100.0, 0.01, 7.0, 3.0, 42.0, 1.0],
    [1.0] * 20,
]


class FixedRandom(Random):
    """Random, у которого `random()` всегда возвращает одно и то же число.

    Позволяет форсировать исход каждого розыгрыша без знания сида.
    """

    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


def _all_k(weights: list[float]) -> list[tuple[list[float], int]]:
    return [(weights, k) for k in range(len(weights) + 1)]


ALL_CASES = [case for weights in WEIGHTS_CASES for case in _all_k(weights)]


# --------------------------------------------------------------------------- #
# sample_weighted_subset
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("weights", "k"), ALL_CASES)
def test_subset_has_exactly_k_strictly_increasing_indices(
    weights: list[float], k: int
) -> None:
    rng = Random(1)
    for _ in range(50):
        chosen = sample_weighted_subset(weights, k, rng)

        assert len(chosen) == k
        assert all(0 <= i < len(weights) for i in chosen)
        assert all(a < b for a, b in itertools.pairwise(chosen))


@pytest.mark.parametrize(("weights", "k"), ALL_CASES)
def test_subset_is_deterministic_for_same_seed(weights: list[float], k: int) -> None:
    rng_a, rng_b = Random(123), Random(123)
    for _ in range(20):
        assert sample_weighted_subset(weights, k, rng_a) == sample_weighted_subset(
            weights, k, rng_b
        )


def test_k_zero_returns_empty_and_does_not_touch_rng() -> None:
    rng = Random(7)
    state = rng.getstate()

    assert sample_weighted_subset([1.0, 2.0, 3.0], 0, rng) == []
    assert rng.getstate() == state


def test_k_equals_n_returns_everything_and_does_not_touch_rng() -> None:
    rng = Random(7)
    state = rng.getstate()

    assert sample_weighted_subset([1.0, 2.0, 3.0], 3, rng) == [0, 1, 2]
    assert rng.getstate() == state


def test_accepts_any_sequence() -> None:
    weights = (1, 2, 3, 4)
    assert sample_weighted_subset(weights, 2, Random(0)) == sample_weighted_subset(
        list(map(float, weights)), 2, Random(0)
    )


def test_does_not_mutate_input() -> None:
    weights = [3.0, 1.0, 2.0, 5.0]
    sample_weighted_subset(weights, 2, Random(0))
    assert weights == [3.0, 1.0, 2.0, 5.0]


@pytest.mark.parametrize("k", [1, 2, 3])
def test_rng_always_zero_takes_first_k(k: int) -> None:
    """random() == 0 → каждая позиция включается, пока не наберётся k."""
    assert sample_weighted_subset([5.0, 1.0, 3.0, 2.0], k, FixedRandom(0.0)) == list(
        range(k)
    )


@pytest.mark.parametrize("k", [1, 2, 3])
def test_rng_almost_one_takes_last_k(k: int) -> None:
    """random() → 1 → ни один розыгрыш не выигрывается, добор идёт с хвоста."""
    rng = FixedRandom(1.0 - 2**-53)
    n = 4
    assert sample_weighted_subset([5.0, 1.0, 3.0, 2.0], k, rng) == list(range(n - k, n))


@pytest.mark.parametrize("power", [-10, -1, 1, 3, 10])
def test_scaling_by_power_of_two_gives_identical_result(power: int) -> None:
    """Модель инвариантна к масштабу весов.

    Умножение на степень двойки в плавающей точке точное, поэтому при
    одинаковом сиде результат должен совпасть побитово, а не только
    по распределению.
    """
    weights = [1.0, 3.0, 0.5, 7.0, 2.0, 11.0]
    scaled = [w * 2.0**power for w in weights]
    rng_a, rng_b = Random(99), Random(99)

    for _ in range(200):
        assert sample_weighted_subset(weights, 3, rng_a) == sample_weighted_subset(
            scaled, 3, rng_b
        )


def test_extreme_weight_ratio_is_stable() -> None:
    """Крайние допустимые веса в одном наборе: без переполнения и NaN."""
    from libs.weighted_subset_sampler._limits import MAX_WEIGHT

    heavy, light = float(MAX_WEIGHT), 1 / MAX_WEIGHT
    rng = Random(0)
    for _ in range(1_000):
        assert sample_weighted_subset([light, heavy, light], 1, rng) == [1]


def test_max_size_input_runs() -> None:
    from libs.weighted_subset_sampler._limits import MAX_SIZE, MAX_WEIGHT

    weights = [float(MAX_WEIGHT) if i % 2 else 1 / MAX_WEIGHT for i in range(MAX_SIZE)]
    chosen = sample_weighted_subset(weights, MAX_SIZE // 2, Random(0))

    assert len(chosen) == MAX_SIZE // 2
    assert chosen == sorted(set(chosen))


# --------------------------------------------------------------------------- #
# sample_weighted_mask
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("weights", "k"), ALL_CASES)
def test_mask_matches_subset(weights: list[float], k: int) -> None:
    rng_mask, rng_subset = Random(5), Random(5)
    for _ in range(20):
        mask = sample_weighted_mask(weights, k, rng_mask)
        chosen = sample_weighted_subset(weights, k, rng_subset)

        assert len(mask) == len(weights)
        assert sum(mask) == k
        assert [i for i, v in enumerate(mask) if v] == chosen
