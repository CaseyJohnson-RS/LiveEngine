"""Защитные тесты численной устойчивости на границах из `_limits`.

Опираются на приватный `_InclusionOdds` намеренно: проверяемый инвариант
(`num > 0` и `den > 0` для всех допустимых `(i, rest)`) — свойство
внутренней таблицы, через публичный интерфейс он виден лишь как
незаметный сдвиг распределения. Если тест упал после изменения `_limits`,
значит новые границы нарушают связь (1 + MAX_WEIGHT) ** MAX_SIZE <= 1e300.
"""

from random import Random

import pytest

from engine.libs.weighted_subset_sampler._limits import MAX_SIZE, MAX_WEIGHT
from engine.libs.weighted_subset_sampler.sampler import (
    _InclusionOdds,  # type: ignore
)


def extreme_patterns(n: int, heavy: float) -> dict[str, list[float]]:
    """Наборы весов, растягивающие разброс значений строки до предела."""
    light = 1 / heavy
    rng = Random(0)
    return {
        "alternating-light-first": [
            heavy if i % 2 else light for i in range(n)
        ],
        "alternating-heavy-first": [
            light if i % 2 else heavy for i in range(n)
        ],
        "heavy-head": [heavy] * (n - n // 2) + [light] * (n // 2),
        "heavy-tail": [light] * (n // 2) + [heavy] * (n - n // 2),
        "all-heavy": [heavy] * n,
        "all-light": [light] * n,
        "random-extremes": [rng.choice((heavy, light)) for _ in range(n)],
    }


def degenerate_odds(weights: list[float]) -> list[tuple[int, int, int]]:
    """Все `(degree, i, rest)`, где предусловия `odds` выполнены, а num или
    den == 0."""
    n = len(weights)
    bad: list[tuple[int, int, int]] = []
    for degree in range(1, n):
        odds = _InclusionOdds(weights, degree)
        for i in range(n):
            for rest in range(1, min(degree, n - i - 1) + 1):
                num, den = odds.odds(i, rest)
                if not (num > 0 and den > 0):
                    bad.append((degree, i, rest))
    return bad


def test_limits_satisfy_documented_relation() -> None:
    assert (1 + MAX_WEIGHT) ** MAX_SIZE <= 10**300


PATTERNS = extreme_patterns(MAX_SIZE, float(MAX_WEIGHT))


@pytest.mark.parametrize("weights", PATTERNS.values(), ids=PATTERNS.keys())
def test_odds_never_degenerate_at_limits(weights: list[float]) -> None:
    bad = degenerate_odds(weights)
    assert not bad, f"{len(bad)} degenerate (degree, i, rest), first: {bad[:5]}"


def test_guard_detects_limits_violation() -> None:
    """Контроль самого теста: за пределами связи вырождение действительно
    ловится.

    60 позиций с весами 1e6 дают разброс ~1e360 — заведомо больше double.
    Вырождаются не все наборы (сейчас — однородные all-heavy/all-light),
    поэтому требуется хотя бы один. Если ни один не вырождается, проверка
    выше ослепла.
    """
    patterns = extreme_patterns(60, 1e6)
    assert any(degenerate_odds(weights) for weights in patterns.values())
