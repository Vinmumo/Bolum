"""Multi-provider consensus.

Runs the prediction pipeline against EVERY active provider, then combines them:
the headline "consensus" is the average of each source's expected goals,
recomputed into a single internally-consistent set of markets, and each source's
own numbers are returned alongside so you can eyeball which looks most accurate.

Providers that fail (rate-limited, team not found, not-yet-implemented scaffold)
are skipped gracefully and reported in `meta.providers_failed` — one flaky API
never breaks the prediction.

Averaging is equal-weight for now. To move to "pick the most accurate", weight
each source in `_consensus` by a backtested accuracy score (see MODEL_NOTES).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.providers.base import FootballDataProvider, ProviderError
from app.services import poisson_model
from app.services.predictor import predict_fixture


def predict_fixture_consensus(
    providers: list[tuple[str, FootballDataProvider]],
    *,
    home_name: str,
    away_name: str,
    league_external_id: int,
    season: int,
    db: Session | None = None,
    persist: bool = True,
) -> dict:
    sources: list[dict] = []
    failed: list[dict] = []

    for entry in providers:
        # (name, provider) or (name, provider, weight) — weight defaults to 1.0
        name, provider = entry[0], entry[1]
        weight = entry[2] if len(entry) > 2 else 1.0
        try:
            payload = predict_fixture(
                provider,
                home_name=home_name,
                away_name=away_name,
                league_external_id=league_external_id,
                season=season,
                provider_name=name,
                db=None,
                persist=False,
            )
            sources.append(
                {
                    "provider": name,
                    "weight": weight,
                    "home_team": payload["home_team"],
                    "away_team": payload["away_team"],
                    "prediction": payload["prediction"],
                    "form": payload["form"],
                    "h2h": payload["h2h"],
                }
            )
        except ProviderError as exc:
            failed.append({"provider": name, "reason": str(exc)})
        except Exception as exc:  # a bad adapter shouldn't 500 the whole request
            failed.append({"provider": name, "reason": f"{type(exc).__name__}: {exc}"})

    if not sources:
        # Nothing succeeded — surface the first real reason.
        reason = failed[0]["reason"] if failed else "No active providers."
        raise ProviderError(reason)

    consensus = _consensus(sources)
    primary = sources[0]
    # Use the richest head-to-head we found for the summary box.
    best_h2h = max(sources, key=lambda s: s["h2h"].get("played", 0))["h2h"]

    payload = {
        "home_team": primary["home_team"],
        "away_team": primary["away_team"],
        "consensus": consensus,
        "sources": [
            {
                "provider": s["provider"],
                "weight": s["weight"],
                "prediction": s["prediction"],
                "form": s["form"],
                "h2h": s["h2h"],
            }
            for s in sources
        ],
        "form": primary["form"],
        "h2h": best_h2h,
        "meta": {
            "providers_used": [s["provider"] for s in sources],
            "providers_failed": failed,
            "source_count": len(sources),
            "season": season,
            "league_external_id": league_external_id,
        },
    }

    if persist and db is not None:
        _log_consensus(db, payload)

    return payload


def _consensus(sources: list[dict]) -> dict:
    """Weighted average of expected goals, then recompute all markets once.

    Weights come from Provider.weight (admin-settable; bump the sources that
    backtest better). Equal weights == plain mean.
    """
    total_w = sum(s.get("weight", 1.0) for s in sources) or 1.0
    xg_home = sum(s["prediction"]["xg_home"] * s.get("weight", 1.0) for s in sources) / total_w
    xg_away = sum(s["prediction"]["xg_away"] * s.get("weight", 1.0) for s in sources) / total_w
    result = poisson_model.predict_from_xg(xg_home, xg_away)
    return result.as_dict()


def _log_consensus(db: Session, payload: dict) -> None:
    c = payload["consensus"]
    row = Prediction(
        league_id=payload["meta"]["league_external_id"],
        home_team=payload["home_team"]["name"],
        away_team=payload["away_team"]["name"],
        xg_home=c["xg_home"],
        xg_away=c["xg_away"],
        prob_home=c["prob_home_win"],
        prob_draw=c["prob_draw"],
        prob_away=c["prob_away_win"],
        result=payload,
        inputs={"meta": payload["meta"], "sources": payload["sources"]},
        provider_name=" + ".join(payload["meta"]["providers_used"]),
    )
    db.add(row)
    db.commit()
