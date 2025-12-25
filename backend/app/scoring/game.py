from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayerState:
    player_id: int
    remaining: int = 501


@dataclass(frozen=True)
class ThrowResult:
    player_id: int
    score: int
    bust: bool
    remaining_after: int


@dataclass
class GameState:
    players: tuple[PlayerState, PlayerState]
    active_player_id: int = 1
    winner_player_id: int | None = None
    last_throw: ThrowResult | None = None
    history: list[ThrowResult] = field(default_factory=list)

    @property
    def is_over(self) -> bool:
        return self.winner_player_id is not None


class Game501TwoPlayer:
    """
    Minimal manual scoring for a single 501 game (2 players).

    Rules (minimal):
    - Start at 501 each.
    - Subtract submitted score from the active player's remaining.
    - If score would go below 0 => bust: no change, turn passes.
    - If score hits exactly 0 => that player wins (game over).
    """

    def __init__(self) -> None:
        self._state = GameState(players=(PlayerState(1, 501), PlayerState(2, 501)))

    def state(self) -> GameState:
        return self._state

    def submit_throw(self, score: int, *, player_id: int | None = None) -> GameState:
        if score < 0 or score > 180:
            raise ValueError("score must be between 0 and 180")

        state = self._state
        if state.is_over:
            raise RuntimeError("game is already over")

        active_id = state.active_player_id
        if player_id is not None and player_id != active_id:
            raise PermissionError("not this player's turn")

        p1, p2 = state.players
        active = p1 if active_id == 1 else p2
        other = p2 if active_id == 1 else p1

        remaining = active.remaining
        bust = score > remaining
        new_remaining = remaining if bust else (remaining - score)

        result = ThrowResult(
            player_id=active_id,
            score=score,
            bust=bust,
            remaining_after=new_remaining,
        )

        winner = active_id if new_remaining == 0 else None
        next_active = active_id if winner is not None else (2 if active_id == 1 else 1)

        new_active_state = PlayerState(active_id, new_remaining)
        if active_id == 1:
            new_players = (new_active_state, other)
        else:
            new_players = (other, new_active_state)

        self._state = GameState(
            players=new_players,
            active_player_id=next_active,
            winner_player_id=winner,
            last_throw=result,
            history=[*state.history, result],
        )
        return self._state

