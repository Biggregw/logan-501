from __future__ import annotations

import math
from dataclasses import dataclass


# Standard dartboard sector order (clockwise), with 20 centered at 12 o'clock.
SECTOR_ORDER: tuple[int, ...] = (
    20,
    1,
    18,
    4,
    13,
    6,
    10,
    15,
    2,
    17,
    3,
    19,
    7,
    16,
    8,
    11,
    14,
    9,
    12,
    5,
)


@dataclass(frozen=True)
class DartboardRingRatios:
    """
    Ring radii expressed as a fraction of the full board radius (double outer).

    These are approximate WDF board proportions (good enough as a starting point),
    and can be tuned later per setup/camera.
    """

    inner_bull_r: float = 0.037  # double bull (50)
    outer_bull_r: float = 0.094  # single bull (25)
    triple_inner_r: float = 0.582
    triple_outer_r: float = 0.629
    double_inner_r: float = 0.953
    double_outer_r: float = 1.000

    def __post_init__(self) -> None:
        vals = (
            self.inner_bull_r,
            self.outer_bull_r,
            self.triple_inner_r,
            self.triple_outer_r,
            self.double_inner_r,
            self.double_outer_r,
        )
        if any(v <= 0 for v in vals):
            raise ValueError("ring ratios must be > 0")
        if not (
            self.inner_bull_r < self.outer_bull_r < self.triple_inner_r < self.triple_outer_r < self.double_inner_r <= self.double_outer_r
        ):
            raise ValueError("ring ratios must be strictly increasing (except double_outer >= double_inner)")


@dataclass(frozen=True)
class DartboardCalibration:
    """
    Pixel-space calibration for a single camera.

    - center_x/center_y: board center in image pixels
    - radius_px: board radius in pixels (outer edge of double ring)
    - rotation_deg: rotation offset applied to the sector mapping.
      0 means 20 is at 12 o'clock. Positive rotates clockwise.
    """

    center_x: float
    center_y: float
    radius_px: float
    rotation_deg: float = 0.0
    rings: DartboardRingRatios = DartboardRingRatios()

    def __post_init__(self) -> None:
        if self.radius_px <= 0:
            raise ValueError("radius_px must be > 0")


@dataclass(frozen=True)
class DartScore:
    x: float
    y: float
    value: int  # 0=miss, 1-20, 25=bull
    multiplier: int  # 0=miss, 1=single, 2=double, 3=triple
    score: int
    ring: str  # miss | single | double | triple | bull | dbull
    sector: int | None  # 1-20 or None for bull/miss
    angle_deg: float
    radius_ratio: float
    confidence: float


def _normalize_angle_deg(a: float) -> float:
    a = a % 360.0
    if a < 0:
        a += 360.0
    return a


def _sector_from_angle_deg(angle_from_up_deg: float) -> int:
    """
    angle_from_up_deg:
      0 at 12 o'clock (20), increasing clockwise.
    """
    angle = _normalize_angle_deg(angle_from_up_deg)
    sector_idx = int(((angle + 9.0) % 360.0) // 18.0)  # 20 is centered on 0°
    return SECTOR_ORDER[sector_idx]


def score_dart_pixel(
    *,
    x: float,
    y: float,
    calib: DartboardCalibration,
    confidence: float = 1.0,
) -> DartScore:
    """
    Convert a single pixel coordinate into a standard dart score using the calibration.

    Coordinates are image pixel coordinates (x right, y down).
    """
    dx = x - calib.center_x
    dy = y - calib.center_y

    r = math.hypot(dx, dy)
    rr = r / calib.radius_px if calib.radius_px else float("inf")

    # Convert to an angle measured from "up" (12 o'clock), clockwise, in degrees.
    # Use a Cartesian-like orientation by flipping y (image y increases down).
    theta = math.degrees(math.atan2(-(dy), dx))  # 0° at +x (right), CCW+
    angle_from_up = _normalize_angle_deg(90.0 - theta)  # 0° at up, CW+
    angle_from_up = _normalize_angle_deg(angle_from_up + calib.rotation_deg)

    # Miss outside the board.
    if rr > calib.rings.double_outer_r:
        return DartScore(
            x=x,
            y=y,
            value=0,
            multiplier=0,
            score=0,
            ring="miss",
            sector=None,
            angle_deg=angle_from_up,
            radius_ratio=rr,
            confidence=max(0.0, min(1.0, confidence)),
        )

    # Bulls.
    if rr <= calib.rings.inner_bull_r:
        return DartScore(
            x=x,
            y=y,
            value=25,
            multiplier=2,
            score=50,
            ring="dbull",
            sector=None,
            angle_deg=angle_from_up,
            radius_ratio=rr,
            confidence=max(0.0, min(1.0, confidence)),
        )
    if rr <= calib.rings.outer_bull_r:
        return DartScore(
            x=x,
            y=y,
            value=25,
            multiplier=1,
            score=25,
            ring="bull",
            sector=None,
            angle_deg=angle_from_up,
            radius_ratio=rr,
            confidence=max(0.0, min(1.0, confidence)),
        )

    sector = _sector_from_angle_deg(angle_from_up)

    # Doubles/triples/singles.
    if calib.rings.double_inner_r <= rr <= calib.rings.double_outer_r:
        mult = 2
        ring = "double"
    elif calib.rings.triple_inner_r <= rr <= calib.rings.triple_outer_r:
        mult = 3
        ring = "triple"
    else:
        mult = 1
        ring = "single"

    return DartScore(
        x=x,
        y=y,
        value=sector,
        multiplier=mult,
        score=sector * mult,
        ring=ring,
        sector=sector,
        angle_deg=angle_from_up,
        radius_ratio=rr,
        confidence=max(0.0, min(1.0, confidence)),
    )


def score_darts(
    darts: list[tuple[float, float, float]],
    *,
    calib: DartboardCalibration,
) -> tuple[list[DartScore], int]:
    """
    Score multiple darts.

    Input items are (x, y, confidence).
    """
    scored: list[DartScore] = [
        score_dart_pixel(x=x, y=y, calib=calib, confidence=conf) for (x, y, conf) in darts
    ]
    return scored, sum(d.score for d in scored)

