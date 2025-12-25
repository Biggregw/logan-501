from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.scoring.game import GameState, ThrowResult
from app.scoring.store import get_store

app = FastAPI(title="Logan 501")
store = get_store()

@app.get("/health")
def health():
    return {"status": "ok"}


class ThrowRequest(BaseModel):
    score: int = Field(..., ge=0, le=180, description="Throw score (0-180)")
    player_id: int | None = Field(
        default=None, ge=1, le=2, description="Optional: validate whose turn it is"
    )


class ThrowResultDTO(BaseModel):
    player_id: int
    score: int
    bust: bool
    remaining_after: int


class PlayerStateDTO(BaseModel):
    player_id: int
    remaining: int


class GameStateDTO(BaseModel):
    players: list[PlayerStateDTO]
    active_player_id: int
    winner_player_id: int | None
    last_throw: ThrowResultDTO | None
    history: list[ThrowResultDTO]


def _throw_to_dto(t: ThrowResult) -> ThrowResultDTO:
    return ThrowResultDTO(
        player_id=t.player_id,
        score=t.score,
        bust=t.bust,
        remaining_after=t.remaining_after,
    )


def _state_to_dto(s: GameState) -> GameStateDTO:
    return GameStateDTO(
        players=[
            PlayerStateDTO(player_id=p.player_id, remaining=p.remaining) for p in s.players
        ],
        active_player_id=s.active_player_id,
        winner_player_id=s.winner_player_id,
        last_throw=_throw_to_dto(s.last_throw) if s.last_throw is not None else None,
        history=[_throw_to_dto(t) for t in s.history],
    )


@app.get("/game", response_model=GameStateDTO)
def get_game_state() -> GameStateDTO:
    return _state_to_dto(store.game().state())


@app.post("/game/throw", response_model=GameStateDTO)
def submit_throw(req: ThrowRequest) -> GameStateDTO:
    try:
        state = store.game().submit_throw(req.score, player_id=req.player_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _state_to_dto(state)
