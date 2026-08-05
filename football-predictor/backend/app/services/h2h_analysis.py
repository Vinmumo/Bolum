"""Head-to-head analysis: a short human summary + tiny model nudges.

Pure functions operating on a normalised list of past meetings. Like form, the
H2H effect is intentionally light (default +/-5%) — a handful of historical
meetings is a small sample and squads change season to season.
See docs/MODEL_NOTES.md.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class H2HMatch:
    home_team_id: int
    away_team_id: int
    home_goals: int
    away_goals: int


@dataclass
class H2HSummary:
    played: int
    team1_wins: int
    team2_wins: int
    draws: int
    team1_goals: int
    team2_goals: int
    text: str


def summarise(matches: list[H2HMatch], team1_id: int, team2_id: int) -> H2HSummary:
    """Aggregate meetings from team1's perspective vs team2 (venue-agnostic)."""
    t1_wins = t2_wins = draws = t1_goals = t2_goals = 0

    for m in matches:
        if team1_id == m.home_team_id:
            t1, t2 = m.home_goals, m.away_goals
        else:
            t1, t2 = m.away_goals, m.home_goals
        t1_goals += t1
        t2_goals += t2
        if t1 > t2:
            t1_wins += 1
        elif t2 > t1:
            t2_wins += 1
        else:
            draws += 1

    played = len(matches)
    if played == 0:
        text = "No recent head-to-head meetings on record."
    else:
        text = (
            f"In the last {played} meetings: {t1_wins} home-side wins, "
            f"{t2_wins} away-side wins, {draws} draw(s) "
            f"({t1_goals}-{t2_goals} on aggregate)."
        )
    return H2HSummary(
        played=played,
        team1_wins=t1_wins,
        team2_wins=t2_wins,
        draws=draws,
        team1_goals=t1_goals,
        team2_goals=t2_goals,
        text=text,
    )


def h2h_multipliers(summary: H2HSummary, weight: float = 0.05) -> tuple[float, float]:
    """Return (team1_mult, team2_mult) based on historical goal share.

    Balanced history -> (1.0, 1.0). A side that has historically outscored the
    other gets a small boost, capped by `weight`.
    """
    total_goals = summary.team1_goals + summary.team2_goals
    if summary.played == 0 or total_goals == 0:
        return 1.0, 1.0

    t1_share = summary.team1_goals / total_goals  # 0..1, 0.5 == balanced
    t1_mult = 1.0 + weight * (t1_share - 0.5) * 2.0
    t2_mult = 1.0 + weight * ((1 - t1_share) - 0.5) * 2.0
    return t1_mult, t2_mult
