from collections.abc import Sequence

from ._limits import MAX_SIZE, MAX_WEIGHT
from .exceptions import (
    SamplingSizeError,
    SamplingSubsetSizeError,
    SamplingWeightError,
)


def validated_weights(weights: Sequence[float]) -> list[float]:
    """Проверяет границы и возвращает копию весов как list[float].

    Копия важна: `weights` — произвольная Sequence, которую вызывающий код
    может изменить между валидацией и использованием.
    """
    n = len(weights)
    if n == 0:
        raise SamplingSizeError("weights must not be empty")
    if n > MAX_SIZE:
        raise SamplingSizeError(f"number of weights must be <= {MAX_SIZE}, got {n}")

    checked: list[float] = []
    for i, w in enumerate(weights):
        value = float(w)
        # Отрицание диапазона, а не два отдельных сравнения: так NaN,
        # для которого любое сравнение ложно, тоже вылетит.
        if not (1 / MAX_WEIGHT <= value <= MAX_WEIGHT):
            raise SamplingWeightError(
                f"weight at {i} must be in [{1 / MAX_WEIGHT}; {MAX_WEIGHT}], got {w!r}"
            )
        checked.append(value)

    return checked


def validated_k(k: int, n: int) -> int:
    """Проверяет k против уже провалидированного n.

    Отдельная проверка `k <= MAX_SIZE` не нужна и была бы недостижимой:
    n <= MAX_SIZE уже гарантировано, а k <= n.
    """
    if not (0 <= k <= n):
        raise SamplingSubsetSizeError(f"k must be in [0; {n}], got {k}")
    return k
