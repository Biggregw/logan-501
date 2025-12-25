from __future__ import annotations

from app.scoring.game import Game501MatchTwoPlayer
from app.scoring.dartboard import DartboardCalibration


class InMemoryGameStore:
    """
    Minimal in-memory store for a single game instance.
    """

    def __init__(self) -> None:
        self._game = Game501MatchTwoPlayer()
        self._dartboard_calibration_by_camera_id: dict[str, DartboardCalibration] = {}
        self._dartboard_reference_jpeg_by_camera_id: dict[str, bytes] = {}

    def game(self) -> Game501MatchTwoPlayer:
        return self._game

    # --- Dartboard scoring (calibration + optional reference frame) ---
    def get_dartboard_calibration(self, camera_id: str) -> DartboardCalibration | None:
        return self._dartboard_calibration_by_camera_id.get(camera_id)

    def set_dartboard_calibration(self, camera_id: str, calib: DartboardCalibration) -> None:
        self._dartboard_calibration_by_camera_id[camera_id] = calib

    def get_dartboard_reference_jpeg(self, camera_id: str) -> bytes | None:
        return self._dartboard_reference_jpeg_by_camera_id.get(camera_id)

    def set_dartboard_reference_jpeg(self, camera_id: str, jpg: bytes) -> None:
        self._dartboard_reference_jpeg_by_camera_id[camera_id] = jpg

    def clear_dartboard_reference(self, camera_id: str) -> None:
        self._dartboard_reference_jpeg_by_camera_id.pop(camera_id, None)


_STORE: InMemoryGameStore | None = None


def get_store() -> InMemoryGameStore:
    global _STORE
    if _STORE is None:
        _STORE = InMemoryGameStore()
    return _STORE

