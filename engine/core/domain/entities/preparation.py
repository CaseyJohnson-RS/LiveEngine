from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet

from engine.core.domain.enums import Item, PreparationPhase
from engine.core.domain.exceptions.preparation import (
    PreparationArgumentError,
    PreparationDecisionError,
    PreparationPhaseError,
)
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import PreparationState, RoundConfig


class Preparation:
    """Подготовка — состояние партии перед раундом.

    Хранит конфигурацию раунда, участников, текущую фазу, выпавшие
    предметы, выбранные руки и раскладки. Правил игры не содержит:
    допустима ли рука (из старой руки и выпавших, не больше лимита),
    тратит ли раскладка весь пул и подтвердили ли все живые — решает
    правило.

    Участники — живые на начало подготовки. Каждый участник принимает
    решение в каждой фазе ровно один раз.

    Ошибки:
    - `ValueError` — неверные параметры создания: их вычисляет движок;
    - наследники `PreparationError` — недопустимое решение игрока.
    """

    __slots__ = (
        "_config",
        "_hands",
        "_layouts",
        "_offers",
        "_participants",
        "_phase",
    )

    def __init__(
        self,
        config: RoundConfig,
        participants: AbstractSet[PlayerID],
        offers: Mapping[PlayerID, Sequence[Item]],
    ) -> None:
        """Создаёт подготовку в фазе выдачи.

        config        — конфигурация раунда.
        participants  — живые игроки на начало подготовки.
        offers        — выпавшие предметы каждого участника: ровно по
                        одной записи на участника, пустая — если ничего
                        не выпало.
        """
        if not participants:
            raise ValueError("participants must not be empty")
        if set(offers) != set(participants):
            raise ValueError(
                f"offers must cover exactly the participants: "
                f"participants {sorted(participants)}, "
                f"offers for {sorted(offers)}"
            )
        # - - -

        self._config = config
        self._participants: frozenset[PlayerID] = frozenset(participants)
        self._phase = PreparationPhase.DEALING
        self._offers: dict[PlayerID, tuple[Item, ...]] = {
            player: tuple(items) for player, items in offers.items()
        }
        self._hands: dict[PlayerID, tuple[Item, ...]] = {}
        self._layouts: dict[PlayerID, tuple[int, ...]] = {}

    # Проверки

    def __check_decision(
        self,
        player: PlayerID,
        phase: PreparationPhase,
        decided: Mapping[PlayerID, object],
    ) -> None:
        """Проверяет, что сейчас нужная фаза, игрок участвует и ещё не решал."""
        if self._phase is not phase:
            raise PreparationPhaseError(
                f"expected phase {phase.name}, current is {self._phase.name}"
            )
        if player not in self._participants:
            raise PreparationDecisionError(
                f"player {player} does not take part in preparation"
            )
        if player in decided:
            raise PreparationDecisionError(
                f"player {player} has already decided in {phase.name}"
            )

    # Конфигурация и фаза

    @property
    def config(self) -> RoundConfig:
        """Конфигурация раунда."""
        return self._config

    @property
    def phase(self) -> PreparationPhase:
        """Текущая фаза."""
        return self._phase

    @property
    def participants(self) -> frozenset[PlayerID]:
        """Участники подготовки."""
        return self._participants

    @property
    def confirmed(self) -> frozenset[PlayerID]:
        """Кто уже принял решение в текущей фазе."""
        decided = (
            self._hands
            if self._phase is PreparationPhase.DEALING
            else self._layouts
        )
        return frozenset(decided)

    def start_placing(self) -> None:
        """Переводит подготовку из выдачи в раскладку. Обратно нельзя.

        Когда переходить — решает правило; повторный переход — баг.
        """
        if self._phase is not PreparationPhase.DEALING:
            raise ValueError(
                f"can start placing only from DEALING, "
                f"current is {self._phase.name}"
            )
        # - - -
        self._phase = PreparationPhase.PLACING

    # Выдача

    def offer(self, player: PlayerID) -> tuple[Item, ...] | None:
        """Выпавшие игроку предметы; None, если он не участник."""
        return self._offers.get(player)

    def hand(self, player: PlayerID) -> tuple[Item, ...] | None:
        """Выбранная рука; None, если игрок ещё не выбрал."""
        return self._hands.get(player)

    def choose_hand(self, player: PlayerID, hand: Sequence[Item]) -> None:
        """Записывает выбранную руку игрока. Решение окончательное.

        Допустима ли рука, проверяет правило до вызова.
        """
        self.__check_decision(player, PreparationPhase.DEALING, self._hands)
        # - - -
        self._hands[player] = tuple(hand)

    # Раскладка

    def layout(self, player: PlayerID) -> tuple[int, ...] | None:
        """Раскладка игрока; None, если он ещё не разложил."""
        return self._layouts.get(player)

    @property
    def layouts(self) -> frozendict[PlayerID, tuple[int, ...]]:
        """Все отправленные раскладки — для зарядки и создания раунда."""
        return frozendict(self._layouts)  # type: ignore

    def place_chips(self, player: PlayerID, layout: Sequence[int]) -> None:
        """Записывает раскладку игрока. Решение окончательное.

        Тратит ли раскладка весь пул, проверяет правило до вызова.
        """
        self.__check_decision(player, PreparationPhase.PLACING, self._layouts)
        if len(layout) != self._config.chambers:
            raise PreparationArgumentError(
                f"layout must have {self._config.chambers} chambers, "
                f"got {len(layout)}"
            )
        if any(chips < 0 for chips in layout):
            raise PreparationArgumentError(
                f"layout must be non-negative, got {tuple(layout)}"
            )
        # - - -
        self._layouts[player] = tuple(layout)

    # Снимок

    @property
    def state(self) -> PreparationState:
        """Полный снимок подготовки, включая скрытое."""
        return PreparationState(
            config=self._config,
            phase=self._phase,
            offers=frozendict(self._offers),  # type: ignore
            hands=frozendict(self._hands),  # type: ignore
            layouts=frozendict(self._layouts),  # type: ignore
        )
