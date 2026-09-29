from collections.abc import Mapping, Sequence

from engine.core.domain.enums import ChamberState
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import RoundState

from .chamber_row import ChamberRow


class Round:
    """Раунд — заряженный ряд и то, что нужно помнить о его зарядке.

    Хранит ряд, раскладки игроков, начальное число патронов и раскрытые
    позиции. Правил игры не содержит: заряжает ряд и решает, кому что
    видно, правило.

    Раскладки и начальное число патронов после создания не меняются.
    Раскрытые позиции только добавляются.

    Ошибки — `ValueError`: нарушить инварианты раунда может только баг в
    правиле, а не выбор игрока.
    """

    __slots__ = ("_initial_cartridges", "_layouts", "_revealed", "_row")

    def __init__(
        self,
        row: ChamberRow,
        layouts: Mapping[PlayerID, Sequence[int]],
        initial_cartridges: int,
    ) -> None:
        """Создаёт раунд из только что заряженного ряда.

        row                 — ряд сразу после зарядки: без отстрелянных камор.
        layouts             — фишки каждого игрока по каморам; длина каждой
                              раскладки — число камор. Игрок без раскладки
                              (выбыл до отправки) в словарь не входит.
        initial_cartridges  — сколько патронов ряд получил при зарядке.
        """
        self.__check_fresh_row(row, initial_cartridges)
        self.__check_layouts(layouts, row.size)
        # - - -

        self._row = row
        self._initial_cartridges = initial_cartridges
        self._layouts: dict[PlayerID, tuple[int, ...]] = {
            player: tuple(layout) for player, layout in layouts.items()
        }
        self._revealed: dict[PlayerID, set[int]] = {}

    # Проверки

    @staticmethod
    def __check_fresh_row(row: ChamberRow, initial_cartridges: int) -> None:
        """Проверяет, что ряд только что заряжен `initial_cartridges`."""
        state = row.state
        if ChamberState.SPENT in state.outcomes:
            raise ValueError("row must be freshly loaded, got spent chambers")
        if state.remain_cartridges != initial_cartridges:
            raise ValueError(
                f"initial_cartridges must match the row: "
                f"row has {state.remain_cartridges}, got {initial_cartridges}"
            )

    @staticmethod
    def __check_layouts(
        layouts: Mapping[PlayerID, Sequence[int]], size: int
    ) -> None:
        """Проверяет, что каждая раскладка покрывает все каморы ряда."""
        for player, layout in layouts.items():
            if len(layout) != size:
                raise ValueError(
                    f"layout of player {player} must have {size} chambers, "
                    f"got {len(layout)}"
                )
            if any(chips < 0 for chips in layout):
                raise ValueError(
                    f"layout of player {player} must be non-negative, "
                    f"got {tuple(layout)}"
                )

    # Ряд и зарядка

    @property
    def row(self) -> ChamberRow:
        """Ряд раунда. Правила работают с ним напрямую."""
        return self._row

    @property
    def initial_cartridges(self) -> int:
        """Сколько патронов ряд получил при зарядке."""
        return self._initial_cartridges

    def layout(self, player: PlayerID) -> tuple[int, ...] | None:
        """Раскладка игрока по каморам; None, если он её не отправил."""
        return self._layouts.get(player)

    # Раскрытые позиции

    def revealed(self, player: PlayerID) -> frozenset[int]:
        """Позиции, раскрытые игроку; пустое множество, если их нет."""
        return frozenset(self._revealed.get(player, ()))

    def reveal(self, player: PlayerID, position: int) -> None:
        """Раскрывает игроку позицию ряда. Повторное раскрытие — no-op."""
        if not (0 <= position < self._row.size):
            raise ValueError(
                f"position must be in [0; {self._row.size}), got {position}"
            )
        # - - -
        self._revealed.setdefault(player, set()).add(position)

    # Снимок

    @property
    def state(self) -> RoundState:
        """Полный снимок раунда, включая скрытое."""
        return RoundState(
            row=self._row.state,
            initial_cartridges=self._initial_cartridges,
            layouts=frozendict(self._layouts),  # type: ignore
            revealed=frozendict(
                {player: frozenset(s) for player, s in self._revealed.items()}  # type: ignore
            ),
        )
