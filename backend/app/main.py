from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.scoring.game import Dart, MatchConfig, MatchState, VisitResult
from app.scoring.store import get_store

app = FastAPI(title="Logan 501")
store = get_store()


@app.get("/health")
def health():
    return {"status": "ok"}


class DartDTO(BaseModel):
    value: int = Field(..., ge=0, le=25, description="0=miss, 1-20, 25=bull")
    multiplier: int = Field(
        ..., ge=0, le=3, description="0=miss, 1=single, 2=double, 3=triple"
    )


class VisitRequest(BaseModel):
    darts: list[DartDTO] = Field(default_factory=list, description="Up to 3 darts in a visit")
    player_id: int | None = Field(
        default=None, ge=1, le=2, description="Optional: validate whose turn it is"
    )


class ResetRequest(BaseModel):
    starting_score: int = Field(default=501, gt=0)
    double_out: bool = Field(default=True)
    legs_to_win_set: int = Field(default=3, gt=0)
    sets_to_win_match: int = Field(default=3, gt=0)


class ConfigDTO(BaseModel):
    starting_score: int
    double_out: bool
    legs_to_win_set: int
    sets_to_win_match: int


class VisitResultDTO(BaseModel):
    player_id: int
    darts: list[DartDTO]
    total: int
    bust: bool
    checkout: bool
    remaining_before: int
    remaining_after: int


class PlayerStateDTO(BaseModel):
    player_id: int
    remaining: int
    legs_won: int
    sets_won: int


class GameStateDTO(BaseModel):
    config: ConfigDTO
    players: list[PlayerStateDTO]
    active_player_id: int
    leg_starter_player_id: int
    set_number: int
    leg_number_in_set: int
    winner_player_id: int | None
    last_leg_winner_player_id: int | None
    last_set_winner_player_id: int | None
    last_visit: VisitResultDTO | None
    history: list[VisitResultDTO]


def _dto_to_darts(darts: list[DartDTO]) -> list[Dart]:
    if len(darts) > 3:
        raise ValueError("a visit may include at most 3 darts")
    return [Dart(value=d.value, multiplier=d.multiplier) for d in darts]


def _visit_to_dto(v: VisitResult) -> VisitResultDTO:
    return VisitResultDTO(
        player_id=v.player_id,
        darts=[DartDTO(value=d.value, multiplier=d.multiplier) for d in v.darts],
        total=v.total,
        bust=v.bust,
        checkout=v.checkout,
        remaining_before=v.remaining_before,
        remaining_after=v.remaining_after,
    )


def _state_to_dto(s: MatchState) -> GameStateDTO:
    return GameStateDTO(
        config=ConfigDTO(
            starting_score=s.config.starting_score,
            double_out=s.config.double_out,
            legs_to_win_set=s.config.legs_to_win_set,
            sets_to_win_match=s.config.sets_to_win_match,
        ),
        players=[
            PlayerStateDTO(
                player_id=p.player_id,
                remaining=p.remaining,
                legs_won=p.legs_won,
                sets_won=p.sets_won,
            )
            for p in s.players
        ],
        active_player_id=s.active_player_id,
        leg_starter_player_id=s.leg_starter_player_id,
        set_number=s.set_number,
        leg_number_in_set=s.leg_number_in_set,
        winner_player_id=s.winner_player_id,
        last_leg_winner_player_id=s.last_leg_winner_player_id,
        last_set_winner_player_id=s.last_set_winner_player_id,
        last_visit=_visit_to_dto(s.last_visit) if s.last_visit is not None else None,
        history=[_visit_to_dto(v) for v in s.history],
    )


@app.get("/game", response_model=GameStateDTO)
def get_game_state() -> GameStateDTO:
    return _state_to_dto(store.game().state())


@app.post("/game/reset", response_model=GameStateDTO)
def reset_game(req: ResetRequest) -> GameStateDTO:
    try:
        state = store.game().reset(
            config=MatchConfig(
                starting_score=req.starting_score,
                double_out=req.double_out,
                legs_to_win_set=req.legs_to_win_set,
                sets_to_win_match=req.sets_to_win_match,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _state_to_dto(state)


@app.post("/game/undo", response_model=GameStateDTO)
def undo_last_visit() -> GameStateDTO:
    try:
        state = store.game().undo()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _state_to_dto(state)


@app.post("/game/visit", response_model=GameStateDTO)
def submit_visit(req: VisitRequest) -> GameStateDTO:
    try:
        darts = _dto_to_darts(req.darts)
        state = store.game().submit_visit(darts, player_id=req.player_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _state_to_dto(state)


# Backwards-compatible route name (treats a "throw" as a full visit).
@app.post("/game/throw", response_model=GameStateDTO)
def submit_throw(req: VisitRequest) -> GameStateDTO:
    return submit_visit(req)
