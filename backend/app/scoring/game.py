from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Dart:
    """
    A single dart hit.

    - value: 1-20 for standard beds, 25 for bull, 0 for a miss
    - multiplier: 0 (miss), 1 (single), 2 (double), 3 (triple)
    """

    value: int
    multiplier: int

    def __post_init__(self) -> None:
        if self.multiplier not in (0, 1, 2, 3):
            raise ValueError("multiplier must be 0, 1, 2, or 3")

        if self.multiplier == 0:
            if self.value != 0:
                raise ValueError("miss must have value=0")
            return

        if self.value not in (*range(1, 21), 25):
            raise ValueError("value must be 1-20, 25 (bull), or 0 (miss)")

        if self.value == 25 and self.multiplier == 3:
            raise ValueError("bull cannot be a triple")

    @property
    def score(self) -> int:
        return self.value * self.multiplier

    @property
    def is_double(self) -> bool:
        return self.multiplier == 2 and self.value in (*range(1, 21), 25)


@dataclass(frozen=True)
class VisitResult:
    """
    Result of a player's visit (up to 3 darts).
    """

    player_id: int
    darts: tuple[Dart, ...]
    total: int
    bust: bool
    checkout: bool
    remaining_before: int
    remaining_after: int


@dataclass(frozen=True)
class PlayerMatchState:
    player_id: int
    remaining: int = 501
    legs_won: int = 0
    sets_won: int = 0


@dataclass(frozen=True)
class MatchConfig:
    starting_score: int = 501
    double_out: bool = True
    legs_to_win_set: int = 3
    sets_to_win_match: int = 3

    def __post_init__(self) -> None:
        if self.starting_score <= 0:
            raise ValueError("starting_score must be > 0")
        if self.legs_to_win_set <= 0:
            raise ValueError("legs_to_win_set must be > 0")
        if self.sets_to_win_match <= 0:
            raise ValueError("sets_to_win_match must be > 0")


@dataclass
class MatchState:
    config: MatchConfig
    players: tuple[PlayerMatchState, PlayerMatchState]
    active_player_id: int = 1
    leg_starter_player_id: int = 1
    set_number: int = 1
    leg_number_in_set: int = 1
    winner_player_id: int | None = None  # match winner
    last_leg_winner_player_id: int | None = None
    last_set_winner_player_id: int | None = None
    last_visit: VisitResult | None = None
    history: tuple[VisitResult, ...] = field(default_factory=tuple)

    @property
    def is_over(self) -> bool:
        return self.winner_player_id is not None


def _other_player_id(player_id: int) -> int:
    if player_id == 1:
        return 2
    if player_id == 2:
        return 1
    raise ValueError("player_id must be 1 or 2")


def _get_player(players: tuple[PlayerMatchState, PlayerMatchState], player_id: int) -> PlayerMatchState:
    if player_id == 1:
        return players[0]
    if player_id == 2:
        return players[1]
    raise ValueError("player_id must be 1 or 2")


def _replace_player(
    players: tuple[PlayerMatchState, PlayerMatchState], updated: PlayerMatchState
) -> tuple[PlayerMatchState, PlayerMatchState]:
    if updated.player_id == 1:
        return (updated, players[1])
    if updated.player_id == 2:
        return (players[0], updated)
    raise ValueError("player_id must be 1 or 2")


class Game501MatchTwoPlayer:
    """
    Standard 501 match (2 players), with legs + sets, bust handling, double-out, and undo.

    This module intentionally contains no web/framework imports.

    Key rules implemented:
    - Each player starts each leg on config.starting_score (default 501).
    - A "visit" is up to 3 darts.
    - Bust: score would go below 0, or (with double-out) leave 1, or checkout not ending on a double.
      On bust, the player's score reverts to the start of the visit and the turn passes.
    - Double-out: to finish (reach exactly 0), the final dart of the visit must be a double
      (including double bull = 50).
    - Winning a leg increments legs. Winning enough legs wins a set. Winning enough sets wins the match.
    - Leg starter alternates each new leg.
    """

    def __init__(self, *, config: MatchConfig | None = None) -> None:
        self._config = config or MatchConfig()
        self._state = MatchState(
            config=self._config,
            players=(
                PlayerMatchState(1, self._config.starting_score, 0, 0),
                PlayerMatchState(2, self._config.starting_score, 0, 0),
            ),
            active_player_id=1,
            leg_starter_player_id=1,
            set_number=1,
            leg_number_in_set=1,
            winner_player_id=None,
            last_leg_winner_player_id=None,
            last_set_winner_player_id=None,
            last_visit=None,
            history=tuple(),
        )
        self._undo_stack: list[MatchState] = []

    def state(self) -> MatchState:
        return self._state

    def reset(self, *, config: MatchConfig | None = None) -> MatchState:
        """
        Reset to a fresh match. If config is provided, it replaces the current config.
        """
        if config is not None:
            self._config = config
        self.__init__(config=self._config)
        return self._state

    def undo(self) -> MatchState:
        """
        Undo the last submitted visit. Raises if there is nothing to undo.
        """
        if not self._undo_stack:
            raise RuntimeError("nothing to undo")
        self._state = self._undo_stack.pop()
        return self._state

    def submit_visit(
        self, darts: Sequence[Dart] | Iterable[Dart], *, player_id: int | None = None
    ) -> MatchState:
        """
        Submit a single visit (up to 3 darts) for the active player.
        """
        state = self._state
        if state.is_over:
            raise RuntimeError("match is already over")

        active_id = state.active_player_id
        if player_id is not None and player_id != active_id:
            raise PermissionError("not this player's turn")

        dart_list = tuple(darts)
        if len(dart_list) == 0:
            # Common scoring apps allow a "no score" visit; treat it as 0 points.
            dart_list = (Dart(0, 0),)
        if len(dart_list) > 3:
            raise ValueError("a visit may include at most 3 darts")

        # Force validation now (useful if an Iterable was passed).
        dart_list = tuple(Dart(d.value, d.multiplier) for d in dart_list)
        total = sum(d.score for d in dart_list)
        if total < 0 or total > 180:
            raise ValueError("visit total must be between 0 and 180")

        active = _get_player(state.players, active_id)
        remaining_before = active.remaining

        # If a visit reaches exactly 0, it must do so on the final dart submitted.
        # (You can't throw extra darts after the leg ends.)
        running = 0
        for i, d in enumerate(dart_list):
            running += d.score
            if running == remaining_before and i != (len(dart_list) - 1):
                raise ValueError("visit includes darts after checkout; submit only darts thrown")

        proposed_remaining = remaining_before - total

        bust = False
        checkout = False
        remaining_after = remaining_before

        if proposed_remaining < 0:
            bust = True
        elif state.config.double_out and proposed_remaining == 1:
            bust = True
        elif proposed_remaining == 0:
            if state.config.double_out:
                if not dart_list[-1].is_double:
                    bust = True
                else:
                    checkout = True
                    remaining_after = 0
            else:
                checkout = True
                remaining_after = 0
        else:
            remaining_after = proposed_remaining

        visit = VisitResult(
            player_id=active_id,
            darts=dart_list,
            total=total,
            bust=bust,
            checkout=checkout,
            remaining_before=remaining_before,
            remaining_after=remaining_after,
        )

        # Save current state for undo.
        self._undo_stack.append(state)

        # Apply score update (or revert on bust).
        new_active = PlayerMatchState(
            player_id=active.player_id,
            remaining=remaining_after if not bust else remaining_before,
            legs_won=active.legs_won,
            sets_won=active.sets_won,
        )
        players_after_score = _replace_player(state.players, new_active)

        # Determine next active player (turn always passes after a visit, including bust/checkout,
        # unless the match ends).
        next_active_player_id = _other_player_id(active_id)

        last_leg_winner_player_id = state.last_leg_winner_player_id
        last_set_winner_player_id = state.last_set_winner_player_id
        winner_player_id = state.winner_player_id

        leg_starter_player_id = state.leg_starter_player_id
        set_number = state.set_number
        leg_number_in_set = state.leg_number_in_set

        if checkout:
            # Leg won.
            last_leg_winner_player_id = active_id

            winner_player = _get_player(players_after_score, active_id)
            winner_player = PlayerMatchState(
                winner_player.player_id,
                winner_player.remaining,
                winner_player.legs_won + 1,
                winner_player.sets_won,
            )
            players_after_score = _replace_player(players_after_score, winner_player)

            # Check for set win.
            set_won = winner_player.legs_won >= state.config.legs_to_win_set
            if set_won:
                last_set_winner_player_id = active_id
                winner_player = PlayerMatchState(
                    winner_player.player_id,
                    winner_player.remaining,
                    legs_won=winner_player.legs_won,  # will be reset below for new set
                    sets_won=winner_player.sets_won + 1,
                )
                players_after_score = _replace_player(players_after_score, winner_player)

                match_won = winner_player.sets_won >= state.config.sets_to_win_match
                if match_won:
                    winner_player_id = active_id
                else:
                    # Start next set (legs reset).
                    set_number = state.set_number + 1
                    leg_number_in_set = 1

                    p1 = _get_player(players_after_score, 1)
                    p2 = _get_player(players_after_score, 2)
                    players_after_score = (
                        PlayerMatchState(1, state.config.starting_score, 0, p1.sets_won),
                        PlayerMatchState(2, state.config.starting_score, 0, p2.sets_won),
                    )
            if winner_player_id is None:
                # Start next leg (scores reset, starter alternates).
                if not set_won:
                    leg_number_in_set = state.leg_number_in_set + 1

                leg_starter_player_id = _other_player_id(state.leg_starter_player_id)
                next_active_player_id = leg_starter_player_id

                # Reset remaining for new leg while keeping legs/sets.
                p1 = _get_player(players_after_score, 1)
                p2 = _get_player(players_after_score, 2)
                players_after_score = (
                    PlayerMatchState(1, state.config.starting_score, p1.legs_won, p1.sets_won),
                    PlayerMatchState(2, state.config.starting_score, p2.legs_won, p2.sets_won),
                )

        self._state = MatchState(
            config=state.config,
            players=players_after_score,
            active_player_id=next_active_player_id if winner_player_id is None else state.active_player_id,
            leg_starter_player_id=leg_starter_player_id,
            set_number=set_number,
            leg_number_in_set=leg_number_in_set,
            winner_player_id=winner_player_id,
            last_leg_winner_player_id=last_leg_winner_player_id,
            last_set_winner_player_id=last_set_winner_player_id,
            last_visit=visit,
            history=(*state.history, visit),
        )
        return self._state

