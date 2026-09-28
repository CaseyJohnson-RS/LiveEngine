from dataclasses import dataclass

from engine.core.domain.enums import ChamberState


@dataclass(frozen=True)
class ChamberRowState:
    """Неизменяемый снимок каморного ряда в конкретный момент времени.

    Естественно, что данная информация должна проходить фильтрацию
    перед тем, как отдаваться наружу.

    - `outcomes`           — состояние каждой каморы по порядку.
    - `weights`            — веса камор, заданные при создании ряда.
    - `remain_cartridges`  — сколько камор сейчас заряжено (`LOADED`).
    """

    outcomes: tuple[ChamberState, ...]
    weights: tuple[int, ...]

    @property
    def remain_cartridges(self) -> int:
        return sum(outcome is ChamberState.LOADED for outcome in self.outcomes)
