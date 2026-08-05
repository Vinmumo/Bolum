"""Gameweek replay backtesting — "what would Bolum have predicted then?"

Honesty rules:
- Predictions use ONLY point-in-time standings (the table as it stood BEFORE the
  gameweek kicked off). Matchday 1 uses the previous season's final table.
- No form/H2H nudges here — the historical standings snapshots don't carry
  reliable form strings, and mixing partly-known inputs would blur what's being
  measured. It's the pure Poisson engine vs reality.

Results persist in `backtest_results`, so the season summary aggregates from
already-replayed gameweeks without any new API calls.

Scoring (focused on overs/unders, per user priority):
- For each goal line (1.5 / 2.5 / 3.5): pick = over if P(over) > 0.5 else under;
  hit = pick matches the actual total. We also store P(over) so the summary can
  report calibration by confidence bucket, not just raw hit rate.
- 1X2 recorded too (pick = argmax probability).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.backtest import BacktestResult
from app.providers.base import (
    FootballDataProvider,
    ProviderError,
    ProviderTeamStats,
)
from app.services import poisson_model
from app.services.poisson_model import GOAL_LINES, TeamStats


def _to_team_stats(ps: ProviderTeamStats) -> TeamStats:
    return TeamStats(
        team_id=ps.team_id,
        name=ps.name,
        games_home=ps.games_home,
        games_away=ps.games_away,
        goals_for_home=ps.goals_for_home,
        goals_against_home=ps.goals_against_home,
        goals_for_away=ps.goals_for_away,
        goals_against_away=ps.goals_against_away,
        recent_form=[],  # deliberately empty — see module docstring
    )


def replay_gameweek(
    provider: FootballDataProvider,
    db: Session,
    *,
    league_external_id: int,
    season: int,
    matchday: int,
    refresh: bool = False,
) -> dict:
    """Replay one past gameweek. Cached in the DB after the first run."""
    stored = _load_stored(db, league_external_id, season, matchday)
    if stored and not refresh:
        return _payload(league_external_id, season, matchday, stored, from_cache=True)

    fixtures = provider.get_fixtures(league_external_id, season, f"Gameweek {matchday}")
    finished = [
        f for f in fixtures
        if f.home_goals is not None and f.away_goals is not None
    ]
    if not finished:
        raise ProviderError(
            f"No finished fixtures for matchday {matchday} of season {season} — "
            "backtests only cover played gameweeks."
        )

    # Stats as they stood BEFORE this gameweek. MD1 -> previous season's table.
    if matchday <= 1:
        stats_map = provider.get_point_in_time_stats(league_external_id, season - 1, None)
    else:
        stats_map = provider.get_point_in_time_stats(league_external_id, season, matchday - 1)

    rows: list[BacktestResult] = []
    skipped: list[str] = []
    for f in finished:
        home_ps = stats_map.get(f.home.id)
        away_ps = stats_map.get(f.away.id)
        if home_ps is None or away_ps is None:
            # e.g. newly promoted team on MD1 — no prior-season row. Be honest
            # and skip rather than predict from nothing.
            skipped.append(f"{f.home.name} vs {f.away.name}")
            continue
        rows.append(
            _score_fixture(
                f, home_ps, away_ps,
                league_external_id=league_external_id, season=season, matchday=matchday,
            )
        )

    if refresh and stored:
        for old in stored:
            db.delete(old)
        db.flush()
    for r in rows:
        db.add(r)
    db.commit()

    payload = _payload(league_external_id, season, matchday, rows, from_cache=False)
    if skipped:
        payload["skipped"] = skipped
    return payload


def _score_fixture(f, home_ps, away_ps, *, league_external_id, season, matchday) -> BacktestResult:
    result = poisson_model.predict(_to_team_stats(home_ps), _to_team_stats(away_ps))
    actual_total = f.home_goals + f.away_goals

    lines: dict[str, dict] = {}
    for line in GOAL_LINES:
        p_over = result.over_lines[f"{line}"]
        pick = "over" if p_over > 0.5 else "under"
        actual = "over" if actual_total > line else "under"
        lines[f"{line}"] = {
            "p_over": round(p_over, 4),
            "pick": pick,
            "actual": actual,
            "hit": pick == actual,
        }

    probs = {
        "home": result.prob_home_win,
        "draw": result.prob_draw,
        "away": result.prob_away_win,
    }
    pick_1x2 = max(probs, key=probs.get)
    actual_1x2 = (
        "home" if f.home_goals > f.away_goals
        else "away" if f.away_goals > f.home_goals
        else "draw"
    )
    return BacktestResult(
        league_id=league_external_id,
        season=season,
        matchday=matchday,
        fixture_ext_id=f.id,
        home_team=f.home.name,
        away_team=f.away.name,
        home_goals=f.home_goals,
        away_goals=f.away_goals,
        xg_home=round(result.xg_home, 3),
        xg_away=round(result.xg_away, 3),
        lines=lines,
        result_1x2={
            "pick": pick_1x2,
            "actual": actual_1x2,
            "hit": pick_1x2 == actual_1x2,
            "p_home": round(probs["home"], 4),
            "p_draw": round(probs["draw"], 4),
            "p_away": round(probs["away"], 4),
        },
    )


def _load_stored(db: Session, league: int, season: int, matchday: int) -> list[BacktestResult]:
    return list(
        db.execute(
            select(BacktestResult).where(
                BacktestResult.league_id == league,
                BacktestResult.season == season,
                BacktestResult.matchday == matchday,
            )
        ).scalars()
    )


def _payload(league, season, matchday, rows: list[BacktestResult], from_cache: bool) -> dict:
    return {
        "league_external_id": league,
        "season": season,
        "matchday": matchday,
        "from_cache": from_cache,
        "fixtures": [
            {
                "home_team": r.home_team,
                "away_team": r.away_team,
                "home_goals": r.home_goals,
                "away_goals": r.away_goals,
                "xg_home": r.xg_home,
                "xg_away": r.xg_away,
                "lines": r.lines,
                "result_1x2": r.result_1x2,
            }
            for r in rows
        ],
    }


# --------------------------------------------------------------------------- #
# Season summary — aggregates whatever gameweeks have been replayed so far.
# --------------------------------------------------------------------------- #
# Confidence buckets for calibration: (label, low, high)
_BUCKETS = [("50-60%", 0.5, 0.6), ("60-70%", 0.6, 0.7), ("70%+", 0.7, 1.01)]


def season_summary(db: Session, *, league_external_id: int, season: int) -> dict:
    rows = list(
        db.execute(
            select(BacktestResult).where(
                BacktestResult.league_id == league_external_id,
                BacktestResult.season == season,
            )
        ).scalars()
    )
    matchdays = sorted({r.matchday for r in rows})

    per_line: dict[str, dict] = {}
    for line in GOAL_LINES:
        key = f"{line}"
        entries = [r.lines[key] for r in rows if key in (r.lines or {})]
        hits = sum(1 for e in entries if e["hit"])
        # Calibration: confidence = probability of the *picked* side.
        buckets = []
        for label, lo, hi in _BUCKETS:
            def conf(e):
                return e["p_over"] if e["pick"] == "over" else 1 - e["p_over"]
            in_bucket = [e for e in entries if lo <= conf(e) < hi]
            b_hits = sum(1 for e in in_bucket if e["hit"])
            buckets.append(
                {
                    "bucket": label,
                    "count": len(in_bucket),
                    "hit_rate": round(b_hits / len(in_bucket), 3) if in_bucket else None,
                }
            )
        per_line[key] = {
            "count": len(entries),
            "hits": hits,
            "hit_rate": round(hits / len(entries), 3) if entries else None,
            "calibration": buckets,
        }

    hits_1x2 = sum(1 for r in rows if (r.result_1x2 or {}).get("hit"))
    return {
        "league_external_id": league_external_id,
        "season": season,
        "fixtures_backtested": len(rows),
        "matchdays_replayed": matchdays,
        "over_under": per_line,
        "result_1x2": {
            "count": len(rows),
            "hits": hits_1x2,
            "hit_rate": round(hits_1x2 / len(rows), 3) if rows else None,
        },
    }
