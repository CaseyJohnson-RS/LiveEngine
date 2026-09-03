from collections.abc import Iterable, Sequence

from engine.core.domain.enums.items import Item
from engine.core.domain.exceptions.player import PlayerArgumentError, PlayerStateError
from engine.core.domain.value_objects.effects import Effect
from engine.core.domain.value_objects.player_state import PlayerState


class Player:
    """Игрок как доменная сущность.

    Не решает сам, когда и почему что-то происходит (чей ход, что делает
    предмет, легальна ли цель — всё это внешние правила), но сам исполняет
    и охраняет свои самодостаточные инварианты: здоровье и фишки не уходят
    в минус, число предметов не превышает лимит, нельзя убрать то, чего нет.

    Пересоздаётся заново на каждую партию, а не переиспользуется — так
    исключается риск забыть обнулить какое-то поле при сбросе.
    """

    def __init__(self, max_items: int):
        """Создаёт игрока без здоровья — set_health_points обязателен перед использованием.

        До вызова set_health_points health_points равен 0, что неотличимо
        от мёртвого игрока (см. is_alive).
        """

        # Party data

        self._max_items = max_items
        self._items: list[Item] = []
        self._effects: list[Effect] = []
        self._health_points: int = 0

        # Round data

        self._max_health_points: int = 0
        self._chips: int = 0
        self._known_weight_indexes: list[int] = []

    # Functions for working with party data

    # Health

    @property
    def is_alive(self) -> bool:
        return self._health_points > 0

    def set_health_points(self, health_points: int) -> None:
        """Задаёт стартовое здоровье — сразу и как текущее, и как потолок.

        Оверхила нет: потолок равен ровно стартовому значению, лечение
        выше него невозможно (см. adjust_health_points).
        """
        if health_points <= 0:
            raise PlayerArgumentError(f"health_points must be > 0, got {health_points}")
        # - - -
        self._health_points = health_points
        self._max_health_points = health_points

    def adjust_health_points(self, delta: int) -> None:
        """Меняет здоровье, зажимая результат в [0; max_health_points].

        Нанесение урона уже мёртвому игроку (health_points == 0) — ошибка,
        а не тихий no-op: цель должна была быть отсечена раньше, на уровне
        выбора цели, а не молча проигнорирована здесь.
        """
        if self._health_points == 0 and delta < 0:
            raise PlayerStateError("Player is already dead! delta can't be < 0!")
        # - - -
        self._health_points = max(
            0, min(self._health_points + delta, self._max_health_points)
        )

    # Items

    def add_items(self, items: Sequence[Item]) -> None:
        """Добавляет предметы. Бросает ошибку, если итог превысит max_items.

        Решение о том, какие именно предметы предложить и что делать при
        превышении лимита (заменить/отклонить) — забота вызывающего кода,
        не этого метода.
        """
        if len(self._items) + len(items) > self._max_items:
            raise PlayerArgumentError(
                f"Player can't have more than {self._max_items} items!"
            )
        # - - -
        self._items.extend(items)

    def remove_item(self, item: Item) -> None:
        """Убирает один предмет. Бросает ошибку, если такого предмета нет."""
        if item not in self._items:
            raise PlayerStateError(f"Player doesn't have item {item.name!r} to remove!")
        # - - -
        self._items.remove(item)

    # Effects

    def add_effect(self, effect: Effect) -> None:
        """Накладывает эффект. Никаких ограничений не проверяется —

        у эффектов, в отличие от предметов, нет собственного лимита или
        инварианта; сами эффекты пассивны и ничего не делают — их читает
        и интерпретирует внешний код при обработке действий.
        """
        self._effects.append(effect)

    def remove_effect(self, effect: Effect) -> None:
        """Снимает эффект. Бросает ошибку, если такого эффекта нет."""
        if effect not in self._effects:
            raise PlayerStateError(
                f"Player doesn't have effect {type(effect).__name__} to remove!"
            )
        # - - -
        self._effects.remove(effect)

    # Functions for working with round data

    # Chips

    def adjust_chips(self, delta: int) -> None:
        """Меняет число фишек. Бросает ошибку, если результат ушёл бы в минус."""
        if self._chips + delta < 0:
            raise PlayerArgumentError(
                f"Chips must be non negative! Current chips {self._chips}, got delta {delta}"
            )
        # - - -
        self._chips += delta

    def pop_chips(self) -> int:
        """Забирает все фишки игрока и обнуляет счётчик, возвращая забранное.

        Используется в фазе раскладки фишек: пул на новый раунд равен
        тому, что игрок накопил риском за предыдущий.
        """
        value, self._chips = self._chips, 0
        return value

    # Known weight indexes

    def reveal_weight_index(self, index: int) -> None:
        """Помечает индекс каморы как известный игроку.

        Верхняя граница индекса не проверяется — размер ряда игроку не
        принадлежит, это забота вызывающего кода. Повторное раскрытие уже
        известного индекса — не ошибка, а no-op.
        """
        if index < 0:
            raise PlayerArgumentError(f"Chamber index must be >= 0, got {index}")
        if index in self._known_weight_indexes:
            return
        # - - -
        self._known_weight_indexes.append(index)

    def reveal_weight_indexes(self, indexes: Iterable[int]) -> None:
        """Пакетная версия reveal_weight_index."""
        for index in indexes:
            self.reveal_weight_index(index)

    def clear_weight_indexes(self) -> None:
        """Сбрасывает раскрытую информацию о весах.

        Вызывается при смене раунда: старые раскрытые индексы относятся к
        уже перезаряженному ряду и больше ничего не значат.
        """
        self._known_weight_indexes.clear()

    # - - -

    def state(self) -> PlayerState:
        """Возвращает неизменяемый снимок текущего состояния игрока."""
        return PlayerState(
            health_points=self._health_points,
            chips=self._chips,
            items=tuple(self._items),
            effects=tuple(self._effects),
            known_weight_indexes=tuple(self._known_weight_indexes),
        )
