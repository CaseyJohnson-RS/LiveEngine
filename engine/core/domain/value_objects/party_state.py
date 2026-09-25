from dataclasses import dataclass

from engine.core.domain.enums import ChamberState
from engine.core.domain.ids import ClientID
from engine.core.domain.value_objects import PlayerState


@dataclass(frozen=True)
class PartyState:
    """Неизменяемый снимок партии, отдаваемый `Party.state()`.

    `move_number` — счётчик ходов на всю партию, не сбрасывается между
    раундами; на нём завязана проверка «давности» пассивных эффектов
    вроде щита.

    `chamber_states`/`chamber_weights` — сырое содержимое текущего ряда,
    включая ещё не отстрелянные каморы. По правилам игры это скрытая
    информация: рассылать этот снимок клиентам как есть нельзя — сначала
    нужна редакция под конкретного получателя, как и для событий выстрела.
    """

    # Party data

    player_states: dict[ClientID, PlayerState]
    turn_order: list[ClientID]
    active_player_index: int
    move_number: int

    # Round data

    round_number: int
    chamber_states: tuple[ChamberState, ...]
    chamber_weights: tuple[int, ...]
