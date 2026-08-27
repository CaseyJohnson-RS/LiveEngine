"""Conditional Poisson sampling (модель Фишера).

Доменные правила модуля:
  * каждый вес лежит в [1/MAX_WEIGHT; MAX_WEIGHT]
  * число весов n лежит в [1; MAX_SIZE]
  * размер выборки k лежит в [0; n] и тем самым тоже не превосходит MAX_SIZE.
"""

import random
from collections.abc import Sequence

from .validation import (
    validated_k,
    validated_weights,
)

__all__ = [
    "sample_weighted_mask",
    "sample_weighted_subset",
]


class _InclusionOdds:
    """Суффиксные элементарные симметрические многочлены весов.

    Внутренняя таблица хранит `row[i][j] = e_j(weights[i:]) / max_l e_l(weights[i:])`,
    то есть каждая строка нормирована СВОИМ множителем. Складывать и сравнивать
    значения из разных строк бессмысленно, поэтому наружу сырые ячейки не
    выдаются вообще: единственный публичный метод возвращает пару чисел из
    одной строки. Это делает ошибку «сравнить table[i][j] с table[i+1][j]»
    невыразимой, а не просто запрещённой комментарием.
    """

    __slots__ = ("_rows", "_weights")

    def __init__(self, weights: list[float], degree: int) -> None:
        n = len(weights)
        rows = [[0.0] * (degree + 1) for _ in range(n + 1)]
        rows[n][0] = 1.0

        for i in range(n - 1, -1, -1):
            cur, nxt, w = rows[i], rows[i + 1], weights[i]
            cur[0] = 1.0
            for j in range(1, degree + 1):
                cur[j] = nxt[j] + w * nxt[j - 1]

            # cur[0] == 1.0, поэтому scale >= 1.0 всегда: проверка scale > 0
            # была бы недостижимой. Нормировка держит все промежуточные
            # значения в [0; 1 + MAX_WEIGHT], то есть переполнение невозможно.
            scale = max(cur)
            if scale != 1.0:
                for j in range(degree + 1):
                    cur[j] /= scale

        self._rows = rows
        self._weights = weights

    def odds(self, i: int, rest: int) -> tuple[float, float]:
        """Шансы включить позицию `i`, когда осталось добрать `rest` штук.

        Возвращает `(num, den)`: вес всех дополнений, содержащих `i`, и вес
        всех дополнений вообще. Оба числа из одной строки таблицы, поэтому
        их отношение корректно.

        Предусловия (обеспечены вызывающим `_sample`): 1 <= rest <= degree и
        rest < n - i. При них den > 0 строго:
          * rest - 1 <= n - i - 2, значит e_{rest-1}(weights[i+1:]) не равен
            нулю структурно;
          * при границах минимальное нормированное значение строки
            до нуля не додавливается;
          * weights[i] >= 1 / MAX_WEIGHT > 0.
        Поэтому ветки «den == 0» здесь нет.
        """
        tail = self._rows[i + 1]
        num = self._weights[i] * tail[rest - 1]
        return num, num + tail[rest]


def _sample(weights: list[float], k: int, rng: random.Random) -> list[int]:
    """Ядро без валидации. Ожидает уже проверенные `weights` и `k`."""
    n = len(weights)
    odds = _InclusionOdds(weights, k)

    chosen: list[int] = []
    rest = k
    for i in range(n):
        if rest == n - i:
            # Оставшихся позиций ровно столько, сколько нужно добрать.
            # Раньше этот случай проходил через розыгрыш и опирался на то,
            # что random() * den < den всегда истинно при den == num. Это
            # неверно с вероятностью 2^-53 (round-half-to-even при num,
            # равном степени двойки). Берём детерминированно.
            chosen.extend(range(i, n))
            break

        num, den = odds.odds(i, rest)
        if rng.random() * den < num:
            chosen.append(i)
            rest -= 1
            if rest == 0:
                break

    # Цикл всегда выходит через break: при i = n - 1 либо rest == 1 == n - i
    # (вынужденная ветка), либо rest == 0 (выход раньше). Проверки
    # «не добрали» после цикла нет, потому что она недостижима.
    return chosen


# --------------------------------------------------------------------------- #
# Публичный интерфейс
# --------------------------------------------------------------------------- #


def sample_weighted_subset(
    weights: Sequence[float], k: int, rng: random.Random
) -> list[int]:
    """Подмножество размера `k`, выбранное пропорционально произведению весов.

    Модель: conditional Poisson sampling (Фишер) — вероятность конкретного
    подмножества пропорциональна произведению весов входящих в него позиций.
    Модель инвариантна к общему масштабу весов: умножение всех весов на
    константу не меняет распределение. Границы [1 / MAX_WEIGHT; MAX_WEIGHT] —
    границы для корректной работы модели.

    Контракт: возвращается ровно `k` индексов, строго по возрастанию.
    Порядок не несёт информации о «первом выбранном» — вызывающий код
    вправе на возрастание опираться.

    Арифметика с плавающей точкой: заявленные шансы и фактическая частота
    совпадают с точностью double, а не точно.
    """
    checked = validated_weights(weights)
    size = validated_k(k, len(checked))
    if size == 0:
        return []
    return _sample(checked, size, rng)


def sample_weighted_mask(
    weights: Sequence[float], k: int, rng: random.Random
) -> list[bool]:
    """То же, что `sample_weighted_subset`, но результат — маска длины n.

    Ровно `k` элементов равны True.
    """
    chosen = sample_weighted_subset(weights, k, rng)
    mask = [False] * len(weights)
    for i in chosen:
        mask[i] = True
    return mask
