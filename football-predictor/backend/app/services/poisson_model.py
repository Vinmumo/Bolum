"""Poisson expected-goals model.

Pure functions — no I/O, no DB, no HTTP. This makes the maths trivial to unit
test (treat it like a calculator) and keeps the "how we predict" logic in one
place, independent of where the numbers came from.

The approach (classic independent-Poisson / Dixon-Coles-lite):

1. From each team's home/away goals, derive four strengths relative to the
   league average: attack@home, attack@away, defense@home, defense@away.
       attack  = (goals scored per game)   / (league avg goals for that venue)
       defense = (goals conceded per game)  / (league avg goals for opp venue)
   A value of 1.0 == exactly league-average.
2. Expected goals for a specific fixture:
       xg_home = home.attack_home * away.defense_away * league.avg_home_goals
       xg_away = away.attack_away * home.defense_home * league.avg_away_goals
3. Optional light multiplicative nudges for recent form and H2H (kept small on
   purpose — see docs/MODEL_NOTES.md for the reasoning).
4. Assume goals ~ Poisson(xg). Build a score matrix P(home=i, away=j) =
   pmf(i; xg_home) * pmf(j; xg_away) and read off every market from it.

See docs/MODEL_NOTES.md for the "why" behind the weights.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# Sensible fallbacks if we can't compute league averages from data.
# Long-run Premier League: home sides score ~1.5, away sides ~1.2 per game.
DEFAULT_AVG_HOME_GOALS = 1.5
DEFAULT_AVG_AWAY_GOALS = 1.2

MAX_GOALS = 10  # score-matrix truncation; P(>10 goals) is negligible


@dataclass
class TeamStats:
    """Everything the model needs about one team, already aggregated."""

    team_id: int
    name: str
    games_home: int
    games_away: int
    goals_for_home: int
    goals_against_home: int
    goals_for_away: int
    goals_against_away: int
    # Most-recent-first, e.g. ["W", "D", "L", "W", "W"]. Optional.
    recent_form: list[str] = field(default_factory=list)

    def _safe(self, num: int, denom: int, fallback: float) -> float:
        return num / denom if denom > 0 else fallback

    def avg_scored_home(self, fallback: float) -> float:
        return self._safe(self.goals_for_home, self.games_home, fallback)

    def avg_conceded_home(self, fallback: float) -> float:
        return self._safe(self.goals_against_home, self.games_home, fallback)

    def avg_scored_away(self, fallback: float) -> float:
        return self._safe(self.goals_for_away, self.games_away, fallback)

    def avg_conceded_away(self, fallback: float) -> float:
        return self._safe(self.goals_against_away, self.games_away, fallback)


@dataclass
class LeagueAverages:
    avg_home_goals: float = DEFAULT_AVG_HOME_GOALS
    avg_away_goals: float = DEFAULT_AVG_AWAY_GOALS


@dataclass
class Adjustments:
    """Multiplicative nudges applied to raw expected goals.

    1.0 == no change. Kept close to 1.0 by callers on purpose.
    """

    home_form: float = 1.0
    away_form: float = 1.0
    home_h2h: float = 1.0
    away_h2h: float = 1.0


@dataclass
class Scoreline:
    home: int
    away: int
    probability: float


@dataclass
class PredictionResult:
    xg_home: float
    xg_away: float
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    prob_over_2_5: float
    prob_under_2_5: float
    prob_btts: float
    top_scorelines: list[Scoreline]

    def as_dict(self) -> dict:
        return {
            "xg_home": round(self.xg_home, 3),
            "xg_away": round(self.xg_away, 3),
            "prob_home_win": round(self.prob_home_win, 4),
            "prob_draw": round(self.prob_draw, 4),
            "prob_away_win": round(self.prob_away_win, 4),
            "prob_over_2_5": round(self.prob_over_2_5, 4),
            "prob_under_2_5": round(self.prob_under_2_5, 4),
            "prob_btts": round(self.prob_btts, 4),
            "top_scorelines": [
                {"home": s.home, "away": s.away, "probability": round(s.probability, 4)}
                for s in self.top_scorelines
            ],
        }


# --------------------------------------------------------------------------- #
# Strengths + expected goals
# --------------------------------------------------------------------------- #
def league_averages_from_teams(teams: list[TeamStats]) -> LeagueAverages:
    """Estimate league scoring rates from whatever teams we have stats for.

    Falls back to sane defaults when data is thin (e.g. only two teams early
    in a season).
    """
    home_goals, home_games, away_goals, away_games = 0, 0, 0, 0
    for t in teams:
        home_goals += t.goals_for_home
        home_games += t.games_home
        away_goals += t.goals_for_away
        away_games += t.games_away

    avg_home = home_goals / home_games if home_games else DEFAULT_AVG_HOME_GOALS
    avg_away = away_goals / away_games if away_games else DEFAULT_AVG_AWAY_GOALS
    # Guard against degenerate zeros.
    return LeagueAverages(
        avg_home_goals=avg_home or DEFAULT_AVG_HOME_GOALS,
        avg_away_goals=avg_away or DEFAULT_AVG_AWAY_GOALS,
    )


def expected_goals(
    home: TeamStats,
    away: TeamStats,
    league: LeagueAverages,
    adj: Adjustments | None = None,
) -> tuple[float, float]:
    adj = adj or Adjustments()

    home_attack = home.avg_scored_home(league.avg_home_goals) / league.avg_home_goals
    away_defense = away.avg_conceded_away(league.avg_home_goals) / league.avg_home_goals
    away_attack = away.avg_scored_away(league.avg_away_goals) / league.avg_away_goals
    home_defense = home.avg_conceded_home(league.avg_away_goals) / league.avg_away_goals

    xg_home = home_attack * away_defense * league.avg_home_goals
    xg_away = away_attack * home_defense * league.avg_away_goals

    xg_home *= adj.home_form * adj.home_h2h
    xg_away *= adj.away_form * adj.away_h2h

    # Clamp to a plausible band so a data glitch can't produce absurd xg.
    return _clamp(xg_home, 0.1, 6.0), _clamp(xg_away, 0.1, 6.0)


# --------------------------------------------------------------------------- #
# Poisson distribution + score matrix
# --------------------------------------------------------------------------- #
def poisson_pmf(k: int, lam: float) -> float:
    """P(X = k) for X ~ Poisson(lam)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam**k / math.factorial(k)


def score_matrix(xg_home: float, xg_away: float, max_goals: int = MAX_GOALS) -> list[list[float]]:
    home_probs = [poisson_pmf(i, xg_home) for i in range(max_goals + 1)]
    away_probs = [poisson_pmf(j, xg_away) for j in range(max_goals + 1)]
    return [[hp * ap for ap in away_probs] for hp in home_probs]


def summarise_matrix(matrix: list[list[float]], top_n: int = 4) -> dict:
    p_home, p_draw, p_away = 0.0, 0.0, 0.0
    p_over, p_btts = 0.0, 0.0
    scorelines: list[Scoreline] = []

    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if i + j > 2:  # over 2.5
                p_over += p
            if i > 0 and j > 0:
                p_btts += p
            scorelines.append(Scoreline(home=i, away=j, probability=p))

    total = p_home + p_draw + p_away or 1.0  # normalise away truncation loss
    scorelines.sort(key=lambda s: s.probability, reverse=True)
    return {
        "prob_home_win": p_home / total,
        "prob_draw": p_draw / total,
        "prob_away_win": p_away / total,
        "prob_over_2_5": p_over / total,
        "prob_under_2_5": 1.0 - p_over / total,
        "prob_btts": p_btts / total,
        "top_scorelines": scorelines[:top_n],
    }


def predict_from_xg(xg_home: float, xg_away: float, top_n: int = 4) -> PredictionResult:
    """Build the full market breakdown from expected goals alone.

    Split out so the consensus/ensemble layer can average expected goals across
    providers and recompute a single, internally-consistent set of markets.
    """
    summary = summarise_matrix(score_matrix(xg_home, xg_away), top_n=top_n)
    return PredictionResult(
        xg_home=xg_home,
        xg_away=xg_away,
        prob_home_win=summary["prob_home_win"],
        prob_draw=summary["prob_draw"],
        prob_away_win=summary["prob_away_win"],
        prob_over_2_5=summary["prob_over_2_5"],
        prob_under_2_5=summary["prob_under_2_5"],
        prob_btts=summary["prob_btts"],
        top_scorelines=summary["top_scorelines"],
    )


def predict(
    home: TeamStats,
    away: TeamStats,
    league: LeagueAverages | None = None,
    adj: Adjustments | None = None,
    top_n: int = 4,
) -> PredictionResult:
    """End-to-end: stats -> expected goals -> full market probabilities."""
    league = league or LeagueAverages()
    xg_home, xg_away = expected_goals(home, away, league, adj)
    return predict_from_xg(xg_home, xg_away, top_n=top_n)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
