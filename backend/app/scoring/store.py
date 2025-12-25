from __future__ import annotations

from app.scoring.game import Game501MatchTwoPlayer


class InMemoryGameStore:
    """
    Minimal in-memory store for a single game instance.
    """

    def __init__(self) -> None:
        self._game = Game501MatchTwoPlayer()

    def game(self) -> Game501MatchTwoPlayer:
        return self._game


_STORE: InMemoryGameStore | None = None


def get_store() -> InMemoryGameStore:
    global _STORE
    if _STORE is None:
        _STORE = InMemoryGameStore()
    return _STORE

