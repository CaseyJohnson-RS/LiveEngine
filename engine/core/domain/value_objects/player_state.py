from dataclasses import dataclass

from engine.core.domain.enums import Item
from engine.core.domain.value_objects import Effect


@dataclass(frozen=True)
class PlayerState:
    """Неизменяемый снимок состояния игрока, отдаваемый Player.state().

    `known_weight_indexes` — индексы камор, чей вес раскрыт игроку предметами.
    Актуальны только в пределах текущего раунда — теряют смысл и очищаются при
    перезарядке ряда.
    """

    # Party data

    health_points: int
    items: tuple[Item, ...]
    effects: tuple[Effect, ...]

    # Round data

    chips: int
    known_weight_indexes: tuple[int, ...]
