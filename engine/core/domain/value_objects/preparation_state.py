from dataclasses import dataclass

from engine.core.domain.enums import Item, PreparationPhase
from engine.core.domain.ids import PlayerID

from .round_config import RoundConfig


@dataclass(frozen=True)
class PreparationState:
    """Неизменяемый снимок подготовки `Preparation`, отдаваемый
    `Preparation.state`.

    Содержит скрытое: чужие выпавшие предметы, руки и раскладки, а также
    число патронов и слои в конфигурации. Что из этого видит конкретный
    игрок, решают правила (см. docs/rules/visibility.md).

    - `config`   — конфигурация раунда.
    - `phase`    — текущая фаза.
    - `offers`   — выпавшие предметы каждого участника.
    - `hands`    — выбранные руки тех, кто уже выбрал.
    - `layouts`  — раскладки тех, кто уже разложил.
    """

    config: RoundConfig
    phase: PreparationPhase
    offers: frozendict[PlayerID, tuple[Item, ...]]
    hands: frozendict[PlayerID, tuple[Item, ...]]
    layouts: frozendict[PlayerID, tuple[int, ...]]
