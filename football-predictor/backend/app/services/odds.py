"""The Odds API integration — bookmaker over/under lines vs the model.

Docs: https://the-odds-api.com/liveapi/guides/v4/
Free tier: 500 credits/month. One call to /sports/{sport}/odds with a single
market+region costs 1 credit and returns totals for EVERY upcoming game in the
league, so with a 1h cache this stays comfortably inside the free tier.

Dormant until THE_ODDS_API_KEY is set in .env — the endpoint then reports
{"configured": false} and the frontend hides the odds panel.

Implied probability: bookmaker decimal odds include a margin ("vig"), so we
normalise: p_over = (1/over_odds) / (1/over_odds + 1/under_odds).
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.cache import cache

BASE_URL = "https://api.the-odds-api.com/v4"

# canonical (API-Football) league id -> The Odds API sport key
SPORT_KEYS: dict[int, str] = {
    39: "soccer_epl",
    140: "soccer_spain_la_liga",
    135: "soccer_italy_serie_a",
    78: "soccer_germany_bundesliga",
    61: "soccer_france_ligue_one",
    2: "soccer_uefa_champs_league",
}


class OddsError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.the_odds_api_key)


def _fetch_league_totals(sport_key: str) -> list[dict]:
    """All upcoming games' totals for a league. Cached 1h. Costs 1 credit."""
    key = f"odds:{sport_key}:totals"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        resp = httpx.get(
            f"{BASE_URL}/sports/{sport_key}/odds",
            params={
                "apiKey": settings.the_odds_api_key,
                "regions": "eu",
                "markets": "totals",
                "oddsFormat": "decimal",
            },
            timeout=15.0,
        )
        if resp.status_code == 401:
            raise OddsError("The Odds API rejected the key.")
        if resp.status_code == 429:
            raise OddsError("The Odds API rate/credit limit reached.")
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise OddsError(f"The Odds API request failed: {exc}") from exc
    cache.set(key, data, 3600)
    return data


def _norm(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def _match_game(games: list[dict], home: str, away: str) -> dict | None:
    """Match by team-name overlap — odds feeds spell names slightly differently."""
    h, a = _norm(home), _norm(away)
    for g in games:
        gh, ga = _norm(g.get("home_team", "")), _norm(g.get("away_team", ""))
        if (h in gh or gh in h) and (a in ga or ga in a):
            return g
    return None


def market_totals(league_external_id: int, home: str, away: str) -> dict:
    """Averaged bookmaker totals lines for one fixture.

    Returns {"configured": bool, "found": bool, "lines": {"2.5": {...}}, ...}
    where each line has the average over/under odds and the margin-free implied
    over probability — directly comparable with the model's over_lines.
    """
    if not is_configured():
        return {"configured": False, "found": False, "lines": {}}

    sport_key = SPORT_KEYS.get(league_external_id)
    if sport_key is None:
        return {"configured": True, "found": False, "lines": {},
                "reason": f"No Odds-API sport mapping for league {league_external_id}."}

    games = _fetch_league_totals(sport_key)
    game = _match_game(games, home, away)
    if game is None:
        return {"configured": True, "found": False, "lines": {},
                "reason": "Fixture not in the odds feed (only near-term games carry odds)."}

    # Collect over/under prices per point across bookmakers.
    per_point: dict[str, dict[str, list[float]]] = {}
    for bm in game.get("bookmakers", []):
        for market in bm.get("markets", []):
            if market.get("key") != "totals":
                continue
            for outcome in market.get("outcomes", []):
                point = outcome.get("point")
                price = outcome.get("price")
                side = (outcome.get("name") or "").lower()  # "over" / "under"
                if point is None or not price or side not in ("over", "under"):
                    continue
                slot = per_point.setdefault(f"{point}", {"over": [], "under": []})
                slot[side].append(float(price))

    lines: dict[str, dict] = {}
    for point, sides in per_point.items():
        if not sides["over"] or not sides["under"]:
            continue
        avg_over = sum(sides["over"]) / len(sides["over"])
        avg_under = sum(sides["under"]) / len(sides["under"])
        inv_o, inv_u = 1 / avg_over, 1 / avg_under
        lines[point] = {
            "avg_over_odds": round(avg_over, 2),
            "avg_under_odds": round(avg_under, 2),
            "implied_p_over": round(inv_o / (inv_o + inv_u), 4),
            "bookmaker_count": len(sides["over"]),
        }

    return {
        "configured": True,
        "found": bool(lines),
        "commence_time": game.get("commence_time"),
        "matched_home": game.get("home_team"),
        "matched_away": game.get("away_team"),
        "lines": lines,
    }
