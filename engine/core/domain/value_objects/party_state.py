from dataclasses import dataclass

from engine.core.domain.enums import ChamberState
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import PlayerState


@dataclass(frozen=True)
class PartyState:
    # Party
    player_states: dict[PlayerID, PlayerState]
    turn_order: list[PlayerID]
    active_player_index: int
    move_number: int

    # Round
    round_number: int
    chamber_states: tuple[ChamberState, ...]
    chamber_weights: tuple[int, ...]
