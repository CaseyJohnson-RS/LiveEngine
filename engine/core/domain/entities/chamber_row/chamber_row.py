from collections.abc import Sequence, Set  # noqa: PYI025
from random import Random

from engine.core.domain.enums import ChamberState
from engine.core.domain.exceptions.chamber_row import ChamberRowError, ChamberStateError
from engine.core.domain.value_objects import ChamberRowState
from engine.core.math.weighted_subset_sampler import (
    sample_weighted_mask,
    sample_weighted_subset,
)

from ._limits import (
    MAX_SIZE,
    MAX_WEIGHT,
)

_UNSPENT: frozenset[ChamberState] = frozenset({ChamberState.EMPTY, ChamberState.LOADED})


class ChamberRow:
    """Каморный ряд — барабан с явно видимыми и выбираемыми каморами.

    В отличие от классической рулетки, порядок камор не скрыт от игрока:
    можно целиться в конкретную позицию. Ряд отвечает за то, чтобы при
    этом вероятностные операции (`shake`, `add_cartridge`,
    `remove_cartridge`) сохраняли заданные веса камор, а не сводились
    к равновероятному выбору.
    """

    def __init__(
        self, weights: Sequence[int], cartridges: int, rng: Random | None = None
    ) -> None:
        """Создаёт ряд заданной длины и сразу расставляет патроны.

        weights     — вес каждой каморы; чем больше вес, тем выше шанс
                      получить патрон при расстановке.
        cartridges  — сколько патронов расставить по ряду.
        rng         — источник случайности; по умолчанию создаётся новый.
        """
        self.__check_weights_cartridges(weights, cartridges)
        # - - -

        self._rng = rng or Random()

        self._weights: tuple[int, ...] = tuple(weights)
        self._outcomes: list[ChamberState] = [
            ChamberState.LOADED if loaded else ChamberState.EMPTY
            for loaded in sample_weighted_mask(weights, cartridges, self._rng)
        ]

    def __get_chambers(self, states: Set[ChamberState]) -> list[int]:
        """Индексы камор, чьё состояние входит в `states`."""
        return [i for i, v in enumerate(self._outcomes) if v in states]

    def __check_position(self, position: int) -> None:
        """Бросает ValueError, если позиции нет в ряду."""
        if not (0 <= position < len(self._weights)):
            raise ValueError(
                f"Position must be in range [0; {len(self._weights)}), got {position}"
            )

    def __check_chamber_state(
        self, state: ChamberState, permitted_states: Set[ChamberState]
    ) -> None:
        """Бросает ChamberStateError, если состояние не входит в допустимые."""
        if state not in permitted_states:
            raise ChamberStateError(
                f"Chamber state must be in {sorted([i.name for i in permitted_states])}, got {state.name}"
            )

    @staticmethod
    def __check_weights_cartridges(weights: Sequence[int], cartridges: int) -> None:
        """Проверяет доменные ограничения на веса и число патронов.

        Веса не должны быть пустыми, их количество и значения — не
        превышать `MAX_SIZE`/`MAX_WEIGHT`, а число патронов — умещаться
        в диапазон [0; число камор].
        """
        if not weights:
            raise ValueError("weights must not be empty")
        if len(weights) > MAX_SIZE:
            raise ValueError(
                f"Chamber row length must be in range [1; {MAX_SIZE}], got {len(weights)}"
            )
        for i, w in enumerate(weights):
            if not (1 <= w <= MAX_WEIGHT):
                raise ValueError(
                    f"weight at {i} must be in range [1; {MAX_WEIGHT}], got {w}"
                )

        if not (0 <= cartridges <= len(weights)):
            raise ValueError(
                f"cartridges must be in [0; {len(weights)}], got {cartridges}"
            )

    def invert(self, position: int) -> None:
        """Переключает камору между EMPTY и LOADED.

        Допустимо только для ещё не отстрелянной каморы: SPENT необратима
        и приведёт к ChamberStateError.
        """
        self.__check_position(position)
        self.__check_chamber_state(self._outcomes[position], _UNSPENT)
        # - - -

        self._outcomes[position] = (
            ChamberState.EMPTY
            if self._outcomes[position] is ChamberState.LOADED
            else ChamberState.LOADED
        )

    def use(self, position: int) -> bool:
        """Стреляет по каморе: переводит её в SPENT и возвращает, был ли патрон.

        Как и `invert`, применим только к ещё не отстрелянной каморе.
        """
        self.__check_position(position)
        self.__check_chamber_state(self._outcomes[position], _UNSPENT)
        # - - -

        state = self._outcomes[position]
        self._outcomes[position] = ChamberState.SPENT

        return state is ChamberState.LOADED

    def add_cartridge(self) -> None:
        """Добавляет патрон в случайную свободную камору.

        Камора выбирается пропорционально своему весу — чем тяжелее
        камора, тем выше шанс, что патрон достанется именно ей.
        Бросает ChamberRowError, если свободных камор не осталось.
        """
        empty_chambers = self.__get_chambers({ChamberState.EMPTY})

        # - - -
        if not empty_chambers:
            raise ChamberRowError("There's no place for cartridge!")
        # - - -

        subweights = [self._weights[i] for i in empty_chambers]

        self._outcomes[
            empty_chambers[sample_weighted_subset(subweights, 1, self._rng)[0]]
        ] = ChamberState.LOADED

    def remove_cartridge(self) -> None:
        """Убирает патрон из случайной заряженной каморы.

        Вес каморы учитывается в обратной пропорции: чем тяжелее камора,
        тем ниже шанс, что патрон уберут именно из неё (симметрично
        `add_cartridge`). Бросает ChamberRowError, если заряженных камор нет.
        """
        loaded_chambers = self.__get_chambers({ChamberState.LOADED})

        # - - -
        if not loaded_chambers:
            raise ChamberRowError("There's no cartridges to remove!")
        # - - -

        subweights = [1 / self._weights[i] for i in loaded_chambers]

        self._outcomes[
            loaded_chambers[sample_weighted_subset(subweights, 1, self._rng)[0]]
        ] = ChamberState.EMPTY

    def shake(self) -> None:
        """Перемешивает ряд: заново расставляет патроны по неотстрелянным каморам.

        Число заряженных камор сохраняется; SPENT-каморы не участвуют
        и не могут стать заряженными.
        """
        loaded_chambers = self.__get_chambers({ChamberState.LOADED})
        unspent_chambers = self.__get_chambers(_UNSPENT)

        if len(unspent_chambers) == 0:
            return

        subweights = [self._weights[i] for i in unspent_chambers]

        for i, loaded in enumerate(
            sample_weighted_mask(subweights, len(loaded_chambers), self._rng)
        ):
            self._outcomes[unspent_chambers[i]] = (
                ChamberState.LOADED if loaded else ChamberState.EMPTY
            )

    def state(self) -> ChamberRowState:
        """Возвращает неизменяемый снимок текущего состояния ряда."""
        return ChamberRowState(
            tuple(self._outcomes),
            self._weights,
            len(self.__get_chambers({ChamberState.LOADED})),
        )
