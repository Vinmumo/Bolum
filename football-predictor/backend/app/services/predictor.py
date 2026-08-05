"""Orchestrator: provider -> stats/form/h2h -> Poisson model -> result dict.

This is the only service that knows about *all* the pieces. Routers call this;
it stays free of FastAPI/HTTP concerns so it's easy to test and reuse.
"""
from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.providers.base import FootballDataProvider
from app.services import form_analysis, h2h_analysis, poisson_model
from app.services.poisson_model import Adjustments, LeagueAverages, TeamStats


def _to_team_stats(ps) -> TeamStats:
    return TeamStats(
        team_id=ps.team_id,
        name=ps.name,
        games_home=ps.games_home,
        games_away=ps.games_away,
        goals_for_home=ps.goals_for_home,
        goals_against_home=ps.goals_against_home,
        goals_for_away=ps.goals_for_away,
        goals_against_away=ps.goals_against_away,
        recent_form=ps.recent_form,
    )


def predict_fixture(
    provider: FootballDataProvider,
    *,
    home_name: str,
    away_name: str,
    league_external_id: int,
    season: int,
    provider_name: str | None = None,
    db: Session | None = None,
    persist: bool = True,
) -> dict:
    """Full prediction for a fixture named by team.

    Steps: resolve teams -> season stats -> recent form -> H2H -> Poisson.
    Returns a JSON-ready dict; optionally logs it to the predictions table.
    """
    home_team = provider.get_team(home_name, league_external_id, season)
    away_team = provider.get_team(away_name, league_external_id, season)

    home_ps = provider.get_team_stats(home_team.id, season, league_external_id)
    away_ps = provider.get_team_stats(away_team.id, season, league_external_id)
    home_stats = _to_team_stats(home_ps)
    away_stats = _to_team_stats(away_ps)

    # League scoring rates: use the calibrated league baseline (defaults are
    # PL-like: ~1.5 home / ~1.2 away goals per game). We deliberately do NOT
    # derive these from just the two fixture teams — a two-team sample of, say,
    # two elite attacks would inflate the "league average" and make every
    # defence look superhuman, deflating xG. See docs/MODEL_NOTES.md.
    league = LeagueAverages()

    # ---- light form + H2H nudges ----
    home_form_mult = form_analysis.form_multiplier(home_stats.recent_form)
    away_form_mult = form_analysis.form_multiplier(away_stats.recent_form)

    h2h_raw = provider.get_h2h(home_team.id, away_team.id)
    h2h_matches = [
        h2h_analysis.H2HMatch(
            home_team_id=m.home_team_id,
            away_team_id=m.away_team_id,
            home_goals=m.home_goals,
            away_goals=m.away_goals,
        )
        for m in h2h_raw
    ]
    h2h_summary = h2h_analysis.summarise(h2h_matches, home_team.id, away_team.id)
    home_h2h_mult, away_h2h_mult = h2h_analysis.h2h_multipliers(h2h_summary)

    adjustments = Adjustments(
        home_form=home_form_mult,
        away_form=away_form_mult,
        home_h2h=home_h2h_mult,
        away_h2h=away_h2h_mult,
    )

    result = poisson_model.predict(home_stats, away_stats, league, adjustments)

    inputs = {
        "league_external_id": league_external_id,
        "season": season,
        "league_averages": asdict(league),
        "home_stats": asdict(home_stats),
        "away_stats": asdict(away_stats),
        "adjustments": asdict(adjustments),
    }

    payload = {
        "home_team": {"id": home_team.id, "name": home_team.name, "logo": home_ps.logo},
        "away_team": {"id": away_team.id, "name": away_team.name, "logo": away_ps.logo},
        "prediction": result.as_dict(),
        "form": {
            "home": home_stats.recent_form,
            "away": away_stats.recent_form,
        },
        "h2h": {
            "played": h2h_summary.played,
            "home_wins": h2h_summary.team1_wins,
            "away_wins": h2h_summary.team2_wins,
            "draws": h2h_summary.draws,
            "summary": h2h_summary.text,
        },
        "meta": {
            "provider": provider_name,
            "season": season,
            "league_external_id": league_external_id,
        },
    }

    if persist and db is not None:
        _log_prediction(db, payload, inputs, provider_name)

    return payload


def _log_prediction(db: Session, payload: dict, inputs: dict, provider_name: str | None) -> None:
    pred = payload["prediction"]
    row = Prediction(
        league_id=inputs["league_external_id"],
        home_team=payload["home_team"]["name"],
        away_team=payload["away_team"]["name"],
        xg_home=pred["xg_home"],
        xg_away=pred["xg_away"],
        prob_home=pred["prob_home_win"],
        prob_draw=pred["prob_draw"],
        prob_away=pred["prob_away_win"],
        result=payload,
        inputs=inputs,
        provider_name=provider_name,
    )
    db.add(row)
    db.commit()
