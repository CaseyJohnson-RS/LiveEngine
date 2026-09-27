"""Статистическая проверка: эмпирическое распределение против точного.

Для conditional Poisson sampling вероятность подмножества S равна
prod(w_i, i ∈ S) / sum(prod(w_j, j ∈ T) по всем T размера k). При малом n
её можно посчитать перебором и сравнить с частотами.

Сид фиксирован, поэтому тесты детерминированы. Допуск — 5 стандартных
отклонений биномиального распределения: ложное срабатывание на корректной
реализации практически невозможно, а систематический сдвиг в несколько
процентов при N = 60 000 ловится уверенно.
"""

import math
from collections import Counter
from itertools import combinations
from random import Random

import pytest

from libs.weighted_subset_sampler import sample_weighted_subset

TRIALS = 60_000
SIGMAS = 5.0

CASES = {
    "uniform": ([1.0] * 5, 2),
    "increasing": ([1.0, 2.0, 3.0, 4.0, 5.0], 2),
    "skewed": ([1.0, 100.0, 1.0, 50.0, 10.0], 3),
    "inverse": ([1 / w for w in (1.0, 2.0, 5.0, 10.0, 20.0)], 2),
    "k1-proportional": ([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], 1),
    "k-near-n": ([3.0, 1.0, 4.0, 1.0, 5.0, 9.0], 5),
}


def exact_subset_probabilities(
    weights: list[float], k: int
) -> dict[tuple[int, ...], float]:
    products = {
        subset: math.prod(weights[i] for i in subset)
        for subset in combinations(range(len(weights)), k)
    }
    total = sum(products.values())
    return {subset: p / total for subset, p in products.items()}


def _within_tolerance(observed: int, p: float, trials: int) -> bool:
    expected = trials * p
    sigma = math.sqrt(trials * p * (1 - p))
    return abs(observed - expected) <= SIGMAS * sigma


@pytest.mark.parametrize(("weights", "k"), CASES.values(), ids=CASES.keys())
def test_subset_frequencies_match_exact_distribution(
    weights: list[float], k: int
) -> None:
    exact = exact_subset_probabilities(weights, k)
    rng = Random(20260927)
    counts = Counter(
        tuple(sample_weighted_subset(weights, k, rng)) for _ in range(TRIALS)
    )

    assert set(counts) <= set(exact), "выбрано подмножество не того размера"
    for subset, p in exact.items():
        assert _within_tolerance(counts[subset], p, TRIALS), (
            f"{subset}: observed {counts[subset]}, expected {TRIALS * p:.1f}"
        )


@pytest.mark.parametrize(("weights", "k"), CASES.values(), ids=CASES.keys())
def test_inclusion_frequencies_match_exact(weights: list[float], k: int) -> None:
    exact = exact_subset_probabilities(weights, k)
    inclusion = [
        sum(p for subset, p in exact.items() if i in subset)
        for i in range(len(weights))
    ]
    rng = Random(42)
    counts = Counter(
        i for _ in range(TRIALS) for i in sample_weighted_subset(weights, k, rng)
    )

    for i, p in enumerate(inclusion):
        if p in (0.0, 1.0):
            continue
        assert _within_tolerance(counts[i], p, TRIALS), (
            f"position {i}: observed {counts[i]}, expected {TRIALS * p:.1f}"
        )


def test_k1_reduces_to_proportional_choice() -> None:
    """Контрольная точка без перебора: при k = 1 P(i) = w_i / sum(w)."""
    weights = [1.0, 2.0, 3.0, 4.0]
    total = sum(weights)
    rng = Random(1)
    counts = Counter(sample_weighted_subset(weights, 1, rng)[0] for _ in range(TRIALS))

    for i, w in enumerate(weights):
        assert _within_tolerance(counts[i], w / total, TRIALS)


def test_inverse_weights_select_complement_of_direct_weights() -> None:
    """Выбор k по весам 1/w распределён как дополнение выбора n - k по весам w.

    prod(1/w_i, i ∈ S) ∝ prod(w_j, j ∉ S). На этом свойстве держится
    симметрия add_cartridge/remove_cartridge в ChamberRow.
    """
    weights = [1.0, 2.0, 5.0, 10.0, 20.0]
    n, k = len(weights), 2

    direct = exact_subset_probabilities(weights, n - k)
    rng = Random(3)
    counts = Counter(
        tuple(sample_weighted_subset([1 / w for w in weights], k, rng))
        for _ in range(TRIALS)
    )

    for subset, p in direct.items():
        complement = tuple(i for i in range(n) if i not in subset)
        assert _within_tolerance(counts[complement], p, TRIALS)
