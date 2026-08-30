from dataclasses import dataclass, field

from engine.core.domain.enums.items import Item
from engine.core.domain.value_objects.effects import Effect


@dataclass
class Player:
    items: list[Item] = field(default_factory=list[Item])
    effects: list[Effect] = field(default_factory=list[Effect])
    health_points: int = 0
    chips: int = 0
