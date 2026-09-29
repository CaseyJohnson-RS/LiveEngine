from collections.abc import Sequence
from random import Random

from engine.core.domain.entities.chamber_row._limits import (
    MAX_SIZE,
    MAX_WEIGHT,
)
from engine.core.domain.enums import ChamberState
from engine.core.domain.exceptions.chamber_row import (
    ChamberPositionError,
    ChamberSpentError,
    ChamberUnavailableError,
)
from engine.core.domain.value_objects import ChamberRowState
from engine.libs.weighted_subset_sampler import (
    sample_weighted_mask,
    sample_weighted_subset,
)


class ChamberRow:
    """Каморный ряд — выложенные в ряд каморы, каждую можно выбрать.

    Порядок камор открыт: игрок сам выбирает, какую камору использовать.
    Скрыто только содержимое. Ряд отвечает за то, чтобы случайные операции
    (`shake`, `add_cartridge`, `remove_cartridge`) учитывали веса камор,
    а не сводились к равновероятному выбору.

    Отстрелянная камора (SPENT) выбывает навсегда: её нельзя ни
    инвертировать, ни потратить повторно, ни зарядить перемешиванием.

    Ошибки:
    - `ValueError` — неверные параметры создания. Их вычисляет движок,
      а не клиент, поэтому это баг, а не отклонённое действие.
    - наследники `ChamberRowError` — недопустимое действие над рядом,
      как правило, из-за выбора игрока.
    """

    __slots__ = ("_outcomes", "_weights")

    def __init__(
        self, weights: Sequence[int], cartridges: int, rng: Random
    ) -> None:
        """Создаёт ряд и сразу расставляет патроны по весам.

        weights     — вес каждой каморы в [1; MAX_WEIGHT]; чем больше
                      вес, тем выше шанс получить патрон.
        cartridges  — сколько патронов расставить, в [0; len(weights)].
        rng         — источник случайности для начальной расстановки.
        """
        self.__check_weights_cartridges(weights, cartridges)
        # - - -

        self._weights: tuple[int, ...] = tuple(weights)
        self._outcomes: list[ChamberState] = [
            ChamberState.LOADED if loaded else ChamberState.EMPTY
            for loaded in sample_weighted_mask(self._weights, cartridges, rng)
        ]

    # Проверки

    @staticmethod
    def __check_weights_cartridges(
        weights: Sequence[int], cartridges: int
    ) -> None:
        """Проверяет параметры создания; бросает ValueError (не доменную)."""
        if not (1 <= len(weights) <= MAX_SIZE):
            raise ValueError(
                f"row length must be in [1; {MAX_SIZE}], got {len(weights)}"
            )
        for i, w in enumerate(weights):
            if not (1 <= w <= MAX_WEIGHT):
                raise ValueError(
                    f"weight at {i} must be in [1; {MAX_WEIGHT}], got {w}"
                )
        if not (0 <= cartridges <= len(weights)):
            raise ValueError(
                f"cartridges must be in [0; {len(weights)}], got {cartridges}"
            )

    def __check_unspent(self, position: int) -> None:
        """Проверяет, что позиция есть в ряду и камора не отстреляна."""
        if not (0 <= position < self.size):
            raise ChamberPositionError(
                f"position must be in [0; {self.size}), got {position}"
            )
        if self._outcomes[position] is ChamberState.SPENT:
            raise ChamberSpentError(f"chamber {position} is already spent")

    # Выборки

    def __chambers(self, *states: ChamberState) -> list[int]:
        """Индексы камор, чьё состояние входит в `states`."""
        return [i for i, s in enumerate(self._outcomes) if s in states]

    @staticmethod
    def __pick_one(
        chambers: list[int], weights: list[float], rng: Random
    ) -> int:
        """Выбирает одну камору из `chambers` пропорционально `weights`."""
        return chambers[sample_weighted_subset(weights, 1, rng)[0]]

    # Вопросы о ряде

    @property
    def size(self) -> int:
        """Число камор в ряду, включая отстрелянные."""
        return len(self._weights)

    @property
    def is_exhausted(self) -> bool:
        """Отстреляны ли все каморы."""
        return all(s is ChamberState.SPENT for s in self._outcomes)

    # Действия над конкретной каморой

    def spend(self, position: int) -> bool:
        """Тратит камору и возвращает, был ли в ней патрон.

        Камора переходит в SPENT. Используется и для выстрела, и для
        предметов, которые тратят камору без выстрела.
        """
        self.__check_unspent(position)
        # - - -
        loaded = self._outcomes[position] is ChamberState.LOADED
        self._outcomes[position] = ChamberState.SPENT
        return loaded

    def invert(self, position: int) -> None:
        """Меняет содержимое каморы: EMPTY ↔ LOADED."""
        self.__check_unspent(position)
        # - - -
        self._outcomes[position] = (
            ChamberState.EMPTY
            if self._outcomes[position] is ChamberState.LOADED
            else ChamberState.LOADED
        )

    # Случайные действия над рядом

    def add_cartridge(self, rng: Random) -> None:
        """Заряжает одну пустую камору, выбранную пропорционально весу.

        Бросает ChamberUnavailableError, если пустых камор нет.
        """
        empty = self.__chambers(ChamberState.EMPTY)
        if not empty:
            raise ChamberUnavailableError("no empty chamber to load")
        # - - -
        chosen = self.__pick_one(
            empty, [float(self._weights[i]) for i in empty], rng
        )
        self._outcomes[chosen] = ChamberState.LOADED

    def remove_cartridge(self, rng: Random) -> None:
        """Разряжает одну заряженную камору, выбранную обратно весу.

        Чем тяжелее камора, тем ниже шанс, что патрон уберут именно из
        неё. Так распределение остающегося набора патронов согласовано
        с `add_cartridge` и начальной расстановкой: вероятность набора
        пропорциональна произведению весов его камор.

        Бросает ChamberUnavailableError, если заряженных камор нет.
        """
        loaded = self.__chambers(ChamberState.LOADED)
        if not loaded:
            raise ChamberUnavailableError("no loaded chamber to unload")
        # - - -
        chosen = self.__pick_one(
            loaded, [1 / self._weights[i] for i in loaded], rng
        )
        self._outcomes[chosen] = ChamberState.EMPTY

    def shake(self, rng: Random) -> None:
        """Заново расставляет патроны по неотстрелянным каморам.

        Число патронов сохраняется, веса учитываются так же, как при
        создании ряда. Отстрелянные каморы не участвуют.

        Бросает ChamberUnavailableError, если неотстрелянных камор нет.
        Если перемешивать нечего (все неотстрелянные пусты или все заряжены),
        ряд не меняется.
        """
        unspent = self.__chambers(ChamberState.EMPTY, ChamberState.LOADED)
        if not unspent:
            raise ChamberUnavailableError("no unspent chamber to shake")
        # - - -
        cartridges = sum(
            self._outcomes[i] is ChamberState.LOADED for i in unspent
        )
        mask = sample_weighted_mask(
            [self._weights[i] for i in unspent], cartridges, rng
        )
        for i, loaded in zip(unspent, mask, strict=True):
            self._outcomes[i] = (
                ChamberState.LOADED if loaded else ChamberState.EMPTY
            )

    # Снимок

    @property
    def state(self) -> ChamberRowState:
        """Полный снимок ряда, включая скрытое содержимое камор."""
        return ChamberRowState(tuple(self._outcomes), self._weights)
