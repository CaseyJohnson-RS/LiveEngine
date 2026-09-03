from collections.abc import Sequence
from random import Random

from engine.core.domain.entities.chamber_row.chamber_row import ChamberRow
from engine.core.domain.entities.player import Player
from engine.core.domain.enums.chamber_state import ChamberState
from engine.core.domain.exceptions import InvariantViolationError
from engine.core.domain.exceptions.party import PartyArgumentError, PartyStateError
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects.party_state import PartyState


class Party:
    def __init__(
        self,
        player_ids: Sequence[PlayerID],
        max_items: int,
        health_points: int,
        rng: Random | None = None,
    ):
        if health_points <= 0:
            raise PartyArgumentError(f"health_points must be > 0, got {health_points}")
        if len(player_ids) < 2:
            raise PartyArgumentError(
                f"Party can't exist with {len(player_ids)} players. Must be at least 2 players"
            )
        # - - -

        self._rng = rng or Random()

        # Party data

        self._players = {
            player_id: Player(max_items, health_points) for player_id in player_ids
        }
        self._turn_order: list[PlayerID] = self._rng.sample(player_ids, len(player_ids))
        self._active_player_index: int = 0
        self._move_number: int = 0

        # Round  data

        self._round_number: int = 0
        self._unsave_chamber_row: ChamberRow | None = None

    # Functions for working with party data

    def count_players_alive(self) -> int:
        if (
            alive_players := sum(
                [int(player.is_alive) for player in self._players.values()]
            )
        ) == 0:
            raise InvariantViolationError("Impossible party state: 0 alive players")
        # - - -
        return alive_players

    def is_party_over(self) -> bool:
        return self.count_players_alive() == 1

    def get_player(self, player_id: PlayerID) -> Player:
        if player_id not in self._players:
            raise PartyArgumentError(f"There's no player with id {player_id}")
        # - - -
        return self._players[player_id]

    def advance_turn(self) -> None:
        if self.is_party_over():
            raise PartyStateError("Party is over, you can't advance turn")
        # - - -
        self._move_number += 1
        for index in range(
            self._active_player_index + 1,
            self._active_player_index + len(self._players),
        ):
            if self._players[self._turn_order[index % len(self._players)]].is_alive:
                self._active_player_index = index % len(self._players)
                break

    # Functions for working with round data

    @property
    def chamber_row(self) -> ChamberRow:
        if self._unsave_chamber_row is None:
            raise PartyStateError(
                "Chamber row must be initialized! Use start_new_round before!"
            )
        return self._unsave_chamber_row

    def is_round_over(self) -> bool:
        return all(
            chamber_state is ChamberState.SPENT
            for chamber_state in self.chamber_row.state().outcomes
        )

    def can_start_new_round(self) -> bool:
        if self.is_party_over():
            return False
        return self._unsave_chamber_row is None or self.is_round_over()

    def start_new_round(self, chamber_row: ChamberRow) -> None:
        if not self.can_start_new_round():
            raise PartyStateError("Can't start new round right now")
        # - - -
        self._round_number += 1
        self._unsave_chamber_row = chamber_row
        for player in self._players.values():
            player.clear_weight_indexes()

    def state(self) -> PartyState:
        chamber_row_state = self.chamber_row.state()
        return PartyState(
            player_states={
                player_id: player.state() for player_id, player in self._players.items()
            },
            turn_order=self._turn_order.copy(),
            active_player_index=self._active_player_index,
            move_number=self._move_number,
            round_number=self._round_number,
            chamber_states=chamber_row_state.outcomes,
            chamber_weights=chamber_row_state.weights,
        )
