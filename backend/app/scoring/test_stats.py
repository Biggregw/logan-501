from app.scoring.game import Dart, Game501MatchTwoPlayer, MatchConfig
from app.scoring.stats import compute_match_stats


def test_stats_exclude_busted_points() -> None:
    g = Game501MatchTwoPlayer(config=MatchConfig(starting_score=10, double_out=True))

    # P1: bust (tries to score 12 from 10)
    g.submit_visit([Dart(4, 3)])

    # P2: scores 6 (10 -> 4)
    g.submit_visit([Dart(6, 1)])

    state = g.state()
    stats = compute_match_stats(state)

    assert stats.player_1.visits == 1
    assert stats.player_1.busts == 1
    assert stats.player_1.scored_points == 0

    assert stats.player_2.visits == 1
    assert stats.player_2.busts == 0
    assert stats.player_2.scored_points == 6


def test_stats_checkout_counts() -> None:
    g = Game501MatchTwoPlayer(config=MatchConfig(starting_score=40, double_out=True))

    # P1: checks out with D20
    g.submit_visit([Dart(20, 2)])

    stats = compute_match_stats(g.state())
    assert stats.player_1.checkouts == 1
    assert stats.player_1.checkout_attempts >= 1

