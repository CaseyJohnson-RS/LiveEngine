from dataclasses import dataclass

from engine.core.domain.enums.items import Item
from engine.core.domain.value_objects.effects import Effect


@dataclass(frozen=True)
class PlayerState:
    health_points: int
    chips: int
    items: tuple[Item, ...]
    effects: tuple[Effect, ...]
    known_weight_indexes: tuple[int, ...]
