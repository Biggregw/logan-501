from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from app.scoring.game import Dart


@dataclass(frozen=True)
class CheckoutSuggestion:
    """
    A single checkout route (1-3 darts) that finishes exactly.
    """

    darts: tuple[Dart, ...]

    @property
    def total(self) -> int:
        return sum(d.score for d in self.darts)

    def as_strings(self) -> list[str]:
        return [_format_dart(d) for d in self.darts]


def _format_dart(d: Dart) -> str:
    if d.multiplier == 0:
        return "MISS"
    if d.value == 25:
        if d.multiplier == 1:
            return "SBULL"
        if d.multiplier == 2:
            return "DBULL"
    prefix = {1: "S", 2: "D", 3: "T"}[d.multiplier]
    return f"{prefix}{d.value}"


def _all_scoring_darts() -> tuple[Dart, ...]:
    darts: list[Dart] = []
    for v in range(1, 21):
        darts.append(Dart(v, 1))
        darts.append(Dart(v, 2))
        darts.append(Dart(v, 3))
    darts.append(Dart(25, 1))
    darts.append(Dart(25, 2))
    return tuple(darts)


ALL_DARTS: tuple[Dart, ...] = _all_scoring_darts()


def _is_valid_finish(last: Dart, *, double_out: bool) -> bool:
    return (not double_out) or last.is_double


def _dart_preference_weight(d: Dart) -> int:
    """
    Lower is better. This encodes typical "best practice" preferences found in
    popular scoring apps:
    - Prefer not using bull unless it is the obvious route.
    - Prefer T20/T19/T18 as setup darts.
    - Prefer common finishing doubles (D20, D16, D18, D10, D8, D12, D6, D4, D2, DBULL).
    """
    # Bull is fine, but usually not preferred as a setup dart.
    if d.value == 25:
        return 60 if d.multiplier == 1 else 30  # DBULL preferred over SBULL

    # Favor common doubles for finishing.
    if d.multiplier == 2:
        common = [20, 16, 18, 10, 8, 12, 6, 4, 2]
        if d.value in common:
            return 0 + common.index(d.value)
        return 15 + (20 - d.value)

    # Prefer triples on 20/19/18 for scoring/setup.
    if d.multiplier == 3:
        if d.value in (20, 19, 18, 17, 16):
            return 5 + (20 - d.value)
        return 25 + (20 - d.value)

    # Singles are mostly used as setup; mildly de-prioritize.
    return 40 + (20 - d.value)


def _route_weight(route: tuple[Dart, ...], *, double_out: bool) -> tuple[int, int, int, int]:
    """
    Sort key for routes. Lower tuples are preferred.
    """
    # 1) fewer darts
    # 2) prefer "nicer" finishing doubles
    # 3) prefer preferred setup darts
    # 4) deterministic tie-breaker on formatted string
    finish = route[-1]
    finish_weight = _dart_preference_weight(finish)

    setup_weight = sum(_dart_preference_weight(d) for d in route[:-1])
    formatted = ",".join(_format_dart(d) for d in route)
    return (len(route), finish_weight, setup_weight, hash(formatted) & 0xFFFF)


@lru_cache(maxsize=4096)
def suggest_checkouts(
    remaining: int, *, double_out: bool = True, max_darts: int = 3, limit: int = 6
) -> tuple[CheckoutSuggestion, ...]:
    """
    Return up to `limit` suggested checkout routes for a given remaining score.

    Notes:
    - For double-out, the highest possible 3-dart checkout is 170.
    - We do not model "board layout" beyond common preferences.
    """
    if remaining <= 0:
        return tuple()
    if max_darts not in (1, 2, 3):
        raise ValueError("max_darts must be 1, 2, or 3")
    if limit <= 0:
        return tuple()

    # Quick impossibility pruning for the typical case.
    if double_out and remaining > 170:
        return tuple()

    suggestions: list[tuple[Dart, ...]] = []

    darts: Iterable[Dart] = ALL_DARTS

    # 1 dart routes
    if max_darts >= 1:
        for d1 in darts:
            if d1.score == remaining and _is_valid_finish(d1, double_out=double_out):
                suggestions.append((d1,))

    # 2 dart routes
    if max_darts >= 2:
        for d1 in darts:
            r1 = remaining - d1.score
            if r1 <= 0:
                continue
            for d2 in darts:
                if d2.score == r1 and _is_valid_finish(d2, double_out=double_out):
                    suggestions.append((d1, d2))

    # 3 dart routes
    if max_darts >= 3:
        for d1 in darts:
            r1 = remaining - d1.score
            if r1 <= 0:
                continue
            for d2 in darts:
                r2 = r1 - d2.score
                if r2 <= 0:
                    continue
                for d3 in darts:
                    if d3.score == r2 and _is_valid_finish(d3, double_out=double_out):
                        suggestions.append((d1, d2, d3))

    suggestions.sort(key=lambda rt: _route_weight(rt, double_out=double_out))

    # Deduplicate by string form (different Dart instances shouldn't happen, but keep it safe).
    seen: set[str] = set()
    out: list[CheckoutSuggestion] = []
    for route in suggestions:
        key = ",".join(_format_dart(d) for d in route)
        if key in seen:
            continue
        seen.add(key)
        out.append(CheckoutSuggestion(darts=route))
        if len(out) >= limit:
            break

    return tuple(out)

