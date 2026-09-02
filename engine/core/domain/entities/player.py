from collections.abc import Iterable, Sequence

from engine.core.domain.enums.items import Item
from engine.core.domain.exceptions.player import PlayerArgumentError, PlayerStateError
from engine.core.domain.value_objects.effects import Effect
from engine.core.domain.value_objects.player_state import PlayerState


class Player:
    def __init__(self, max_items: int):
        self._max_items = max_items
        self._max_health_points: int = 0

        self._health_points: int = 0
        self._chips: int = 0

        self._items: list[Item] = []
        self._effects: list[Effect] = []
        self._known_weight_indexes: list[int] = []

    # Round living objects

    # Chips

    def adjust_chips(self, delta: int) -> None:
        if self._chips + delta < 0:
            raise PlayerArgumentError(
                f"Chips must be non negative! Current chips {self._chips}, got delta {delta}"
            )
        # - - -
        self._chips += delta

    def pop_chips(self) -> int:
        value, self._chips = self._chips, 0
        return value

    # Known weight indexes

    def reveal_weight_index(self, index: int) -> None:
        if index < 0:
            raise PlayerArgumentError(f"Chamber index must be >= 0, got {index}")
        if index in self._known_weight_indexes:
            return
        # - - -
        self._known_weight_indexes.append(index)

    def reveal_weight_indexes(self, indexes: Iterable[int]) -> None:
        for index in indexes:
            self.reveal_weight_index(index)

    def clear_weight_indexes(self) -> None:
        self._known_weight_indexes.clear()

    # Party living objects

    # Health

    def set_health_points(self, health_points: int) -> None:
        if health_points <= 0:
            raise PlayerArgumentError(f"health_points must be > 0, got {health_points}")
        # - - -
        self._health_points = health_points
        self._max_health_points = health_points

    def adjust_health_points(self, delta: int) -> None:
        if self._health_points == 0 and delta < 0:
            raise PlayerStateError("Player is already dead! delta can't be < 0!")
        # - - -
        self._health_points = max(
            0, min(self._health_points + delta, self._max_health_points)
        )

    # Items

    def add_items(self, items: Sequence[Item]) -> None:
        if len(self._items) + len(items) > self._max_items:
            raise PlayerArgumentError(
                f"Player can't have more than {self._max_items} items!"
            )
        # - - -
        self._items.extend(items)

    def remove_item(self, item: Item) -> None:
        if item not in self._items:
            raise PlayerStateError(f"Player doesn't have item {item.name!r} to remove!")
        # - - -
        self._items.remove(item)

    # Effects

    def add_effect(self, effect: Effect) -> None:
        self._effects.append(effect)

    def remove_effect(self, effect: Effect) -> None:
        if effect not in self._effects:
            raise PlayerStateError(
                f"Player doesn't have effect {type(effect).__name__} to remove!"
            )
        # - - -
        self._effects.remove(effect)

    # Other

    @property
    def is_alive(self) -> bool:
        return self._health_points > 0

    def state(self) -> PlayerState:
        return PlayerState(
            health_points=self._health_points,
            chips=self._chips,
            items=tuple(self._items),
            effects=tuple(self._effects),
            known_weight_indexes=tuple(self._known_weight_indexes),
        )
