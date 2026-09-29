from dataclasses import dataclass

from engine.core.domain.enums import Item

from .effects import Effect


@dataclass(frozen=True)
class SeatState:
    """Неизменяемый снимок места `Seat`, отдаваемый `Seat.state`.

    Всё о месте видят все игроки (см. docs/rules/visibility.md), поэтому
    снимок можно отдавать как есть.
    """

    health_points: int
    items: tuple[Item, ...]
    effects: tuple[Effect, ...]

    chips: int
