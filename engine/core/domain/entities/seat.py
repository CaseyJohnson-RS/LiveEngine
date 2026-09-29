from collections.abc import Sequence

from engine.core.domain.enums import Item
from engine.core.domain.exceptions.seat import (
    SeatArgumentError,
    SeatStateError,
)
from engine.core.domain.value_objects import Effect, SeatState


class Seat:
    """Место игрока за столом партии — запись его игровых характеристик.

    Создаётся заново на каждую партию, а не сбрасывается.

    Мёртвое место замораживается. Менять после смерти можно только
    предметы: их могут забрать другие места.

    Использующий код должен помнить об этом.
    """

    __slots__ = (
        "_chips",
        "_effects",
        "_health_points",
        "_items",
        "_max_health_points",
        "_max_items",
    )

    def __init__(self, max_items: int, health_points: int) -> None:
        """Создаёт место с полным здоровьем, без фишек и предметов.

        max_items      — сколько предметов можно держать одновременно.
        health_points  — стартовое и одновременно максимальное здоровье.
        """

        if health_points <= 0:
            raise SeatArgumentError(
                f"health_points must be > 0, got {health_points}"
            )
        if max_items < 0:
            raise SeatArgumentError(f"max_items must be >= 0, got {max_items}")
        # - - -

        self._max_health_points: int = health_points
        self._max_items = max_items

        self._items: list[Item] = []
        self._effects: list[Effect] = []
        self._health_points: int = health_points

        self._chips: int = 0

    def __check_is_alive(self) -> None:
        """Бросает ошибку состояния, если число очков равно нулю."""
        if not self.is_alive:
            raise SeatStateError("Seat is out of health points!")

    # Health

    @property
    def is_alive(self) -> bool:
        """Остались ли у места жизни."""
        return self._health_points > 0

    @property
    def health_points(self) -> int:
        """Очки жизней. Ограничения:

        1. Нельзя изменить число жизней у мертвого.
        2. Нельзя задать вне интервала [0; max_health_points].
        """
        return self._health_points

    @health_points.setter
    def health_points(self, value: int) -> None:
        self.__check_is_alive()
        if not (0 <= value <= self._max_health_points):
            raise SeatArgumentError(
                f"health_points must be in range "
                f"[0; {self._max_health_points}], got {value}"
            )
        # - - -
        self._health_points = value

    # Items

    @property
    def items(self) -> tuple[Item, ...]:
        """Кортеж предметов. Ограничения:

        1. Нельзя взять предметов больше, чем max_items.
        """
        return tuple(self._items)

    @items.setter
    def items(self, items: Sequence[Item]) -> None:
        if len(items) > self._max_items:
            raise SeatArgumentError(
                f"Seat can't have more than {self._max_items} items! "
                f"Got {len(items)}"
            )
        # - - -
        self._items = list(items)

    # Effects

    @property
    def effects(self) -> tuple[Effect, ...]:
        """Кортеж эффектов. Ограничения:

        1. Нельзя переписывать эффекты мертвого.
        """
        return tuple(self._effects)

    @effects.setter
    def effects(self, effects: Sequence[Effect]) -> None:
        self.__check_is_alive()
        # - - -
        self._effects = list(effects)

    # Chips

    @property
    def chips(self) -> int:
        """Количество фишек. Ограничения:

        1. Нельзя изменить число фишек у мертвого.
        2. Нельзя задать число меньше 0.
        """
        return self._chips

    @chips.setter
    def chips(self, chips: int) -> None:
        self.__check_is_alive()
        if chips < 0:
            raise SeatArgumentError(f"chips must be >= 0, got {chips}")
        # - - -
        self._chips = chips

    # State

    @property
    def state(self) -> SeatState:
        """Неизменяемый снимок текущего состояния места."""
        return SeatState(
            health_points=self._health_points,
            chips=self._chips,
            items=tuple(self._items),
            effects=tuple(self._effects),
        )
