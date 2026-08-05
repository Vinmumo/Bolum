# Adding / enabling a league

Leagues are database rows, not code. No redeploy.

## From the admin UI (the normal way)

1. Find the league's id **in the active provider's namespace**. For API-Football,
   common ones:

   | League | id |
   |--------|----|
   | Premier League (England) | 39 |
   | La Liga (Spain) | 140 |
   | Serie A (Italy) | 135 |
   | Bundesliga (Germany) | 78 |
   | Ligue 1 (France) | 61 |
   | Champions League | 2 |

   You can also list what the provider knows via the provider's `get_leagues()`
   (exposed for the active provider through the codebase; API-Football's
   `/leagues` endpoint is the source).

2. `/admin` → **Leagues** → **Add league**:
   - **Name** (display), **Country**
   - **Provider league id** (e.g. `140` for La Liga)
   - **Season** (free API-Football tiers are limited to older seasons, e.g. `2023`)
   - **Active** ✔

3. Save. It appears immediately in the public nav's **league switcher**, and the
   dashboard/predictions default to the first active league.

## Notes

- `external_provider_id` is provider-specific. If you switch providers, the ids
  may differ — update the league rows accordingly.
- The prediction model needs no per-league configuration; it calibrates from the
  league baseline in `poisson_model.py`. If a league scores very differently from
  the Premier League and you want tighter calibration, adjust
  `DEFAULT_AVG_HOME_GOALS` / `DEFAULT_AVG_AWAY_GOALS` or pass a per-league
  `LeagueAverages` (see [MODEL_NOTES.md](MODEL_NOTES.md)).

## Seeding on a fresh DB

`app/db/seed.py` creates one active league (Premier League) on first run. Add
more here if you want them to exist out of the box, or just use the admin UI.
