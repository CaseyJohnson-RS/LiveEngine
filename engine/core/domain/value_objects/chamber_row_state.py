from dataclasses import dataclass

from engine.core.domain.enums import ChamberState


@dataclass(frozen=True)
class ChamberRowState:
    """Неизменяемый снимок каморного ряда в конкретный момент времени.

    outcomes           — состояние каждой каморы по порядку.
    weights            — веса камор, заданные при создании ряда.
    remain_cartridges  — сколько камор сейчас заряжено (LOADED).
    """

    outcomes: tuple[ChamberState, ...]
    weights: tuple[int, ...]
    remain_cartridges: int
