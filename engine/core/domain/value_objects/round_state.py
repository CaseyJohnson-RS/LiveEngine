from dataclasses import dataclass

from engine.core.domain.ids import PlayerID

from .chamber_row_state import ChamberRowState


@dataclass(frozen=True)
class RoundState:
    """Неизменяемый снимок раунда `Round`, отдаваемый `Round.state`.

    Содержит скрытое: содержимое ряда и раскладки всех игроков. Что из
    этого видит конкретный игрок, решают правила (см.
    docs/rules/visibility.md), поэтому снимок как есть наружу не отдаётся.

    - `row`                 — снимок ряда.
    - `initial_cartridges`  — сколько патронов ряд получил при зарядке.
    - `layouts`             — фишки каждого игрока по каморам.
    - `revealed`            — позиции, раскрытые каждому игроку.
    """

    row: ChamberRowState
    initial_cartridges: int
    layouts: frozendict[PlayerID, tuple[int, ...]]
    revealed: frozendict[PlayerID, frozenset[int]]
