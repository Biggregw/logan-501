from __future__ import annotations

from dataclasses import dataclass

from app.scoring.game import MatchState, VisitResult


@dataclass(frozen=True)
class PlayerStats:
    player_id: int
    visits: int
    darts_thrown: int
    scored_points: int
    busts: int
    checkouts: int
    checkout_attempts: int
    highest_visit: int
    count_180: int
    count_140_plus: int
    count_100_plus: int

    @property
    def three_dart_average(self) -> float:
        if self.darts_thrown == 0:
            return 0.0
        return (self.scored_points / self.darts_thrown) * 3.0

    @property
    def checkout_percentage(self) -> float:
        if self.checkout_attempts == 0:
            return 0.0
        return (self.checkouts / self.checkout_attempts) * 100.0


@dataclass(frozen=True)
class MatchStats:
    player_1: PlayerStats
    player_2: PlayerStats


def _is_checkout_attempt(v: VisitResult, *, double_out: bool) -> bool:
    """
    Heuristic: a 'checkout attempt' is any visit that starts on a finishable score.
    """
    if v.remaining_before <= 1:
        return False
    if double_out:
        return v.remaining_before <= 170
    return v.remaining_before <= 180


def _accumulate(player_id: int, visits: list[VisitResult], *, double_out: bool) -> PlayerStats:
    v_for_player = [v for v in visits if v.player_id == player_id]

    darts_thrown = sum(len(v.darts) for v in v_for_player)
    busts = sum(1 for v in v_for_player if v.bust)
    checkouts = sum(1 for v in v_for_player if v.checkout)
    checkout_attempts = sum(1 for v in v_for_player if _is_checkout_attempt(v, double_out=double_out))

    # Typical stats exclude busted points (score reverts).
    scored_points = sum(v.total for v in v_for_player if not v.bust)

    valid_totals = [v.total for v in v_for_player if not v.bust]
    highest_visit = max(valid_totals) if valid_totals else 0

    count_180 = sum(1 for v in v_for_player if (not v.bust and v.total == 180))
    count_140_plus = sum(1 for v in v_for_player if (not v.bust and v.total >= 140))
    count_100_plus = sum(1 for v in v_for_player if (not v.bust and v.total >= 100))

    return PlayerStats(
        player_id=player_id,
        visits=len(v_for_player),
        darts_thrown=darts_thrown,
        scored_points=scored_points,
        busts=busts,
        checkouts=checkouts,
        checkout_attempts=checkout_attempts,
        highest_visit=highest_visit,
        count_180=count_180,
        count_140_plus=count_140_plus,
        count_100_plus=count_100_plus,
    )


def compute_match_stats(state: MatchState) -> MatchStats:
    history = list(state.history)
    return MatchStats(
        player_1=_accumulate(1, history, double_out=state.config.double_out),
        player_2=_accumulate(2, history, double_out=state.config.double_out),
    )

