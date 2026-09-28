from dataclasses import dataclass

from engine.core.domain.enums import Item

from .effects import Effect


@dataclass(frozen=True)
class SeatState:
    """Неизменяемый снимок места `Seat`, отдаваемый `Seat.state`.

    Содержит всё, включая то, что по смыслу известно только владельцу
    места (`known_weight_indexes`). Перед отправкой другим игрокам нужна
    проекция под получателя — снимок как есть рассылать нельзя.

    `known_weight_indexes` — позиции ряда, чей вес раскрыт владельцу
    предметами. Актуальны только в пределах текущего раунда.
    """

    health_points: int
    items: tuple[Item, ...]
    effects: tuple[Effect, ...]

    chips: int
    known_weight_indexes: frozenset[int]
