"""Turn a run of recent results into a small multiplicative adjustment.

Pure functions. The output feeds Adjustments.home_form / away_form in the
Poisson model. We keep the effect deliberately small (default +/-8%): recent
form is signal, but the season-long attack/defence strengths already carry most
of the information, and over-weighting a hot streak overfits noise.
See docs/MODEL_NOTES.md.
"""
from __future__ import annotations

POINTS = {"W": 3, "D": 1, "L": 0}


def form_points_ratio(recent_form: list[str]) -> float:
    """0.0 (all losses) .. 1.0 (all wins). Returns 0.5 when we have no data."""
    if not recent_form:
        return 0.5
    got = sum(POINTS.get(r.upper(), 0) for r in recent_form)
    possible = 3 * len(recent_form)
    return got / possible if possible else 0.5


def form_multiplier(recent_form: list[str], weight: float = 0.08) -> float:
    """Map form ratio to a multiplier around 1.0.

    ratio 0.5 (average) -> 1.0
    ratio 1.0 (perfect) -> 1 + weight
    ratio 0.0 (dire)    -> 1 - weight
    """
    ratio = form_points_ratio(recent_form)
    return 1.0 + weight * (ratio - 0.5) * 2.0
