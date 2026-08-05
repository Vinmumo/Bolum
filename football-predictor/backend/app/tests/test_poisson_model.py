"""The Poisson model is a pure function — test it like a calculator."""
import math

from app.services import poisson_model as pm
from app.services.poisson_model import (
    Adjustments,
    LeagueAverages,
    TeamStats,
    expected_goals,
    poisson_pmf,
    predict,
    score_matrix,
    summarise_matrix,
)


def _team(name, gfh, gah, gfa, gaa, form=None):
    return TeamStats(
        team_id=abs(hash(name)) % 1000,
        name=name,
        games_home=19,
        games_away=19,
        goals_for_home=gfh,
        goals_against_home=gah,
        goals_for_away=gfa,
        goals_against_away=gaa,
        recent_form=form or [],
    )


def test_poisson_pmf_matches_known_values():
    # P(X=0; lam=1) = e^-1
    assert math.isclose(poisson_pmf(0, 1.0), math.exp(-1), rel_tol=1e-9)
    # P(X=2; lam=2) = e^-2 * 2^2 / 2! = 2 e^-2
    assert math.isclose(poisson_pmf(2, 2.0), 2 * math.exp(-2), rel_tol=1e-9)


def test_poisson_pmf_zero_lambda():
    assert poisson_pmf(0, 0.0) == 1.0
    assert poisson_pmf(3, 0.0) == 0.0


def test_score_matrix_sums_to_one():
    total = sum(sum(row) for row in score_matrix(1.5, 1.2))
    assert math.isclose(total, 1.0, abs_tol=1e-4)


def test_summarise_probabilities_normalised():
    s = summarise_matrix(score_matrix(1.6, 1.1))
    assert math.isclose(
        s["prob_home_win"] + s["prob_draw"] + s["prob_away_win"], 1.0, abs_tol=1e-6
    )
    assert math.isclose(s["prob_over_2_5"] + s["prob_under_2_5"], 1.0, abs_tol=1e-6)


def test_average_teams_give_league_average_xg():
    # A perfectly league-average team vs another -> xg equals league averages.
    league = LeagueAverages(avg_home_goals=1.5, avg_away_goals=1.2)
    avg_home = _team("H", gfh=int(1.5 * 19), gah=int(1.2 * 19), gfa=int(1.2 * 19), gaa=int(1.5 * 19))
    avg_away = _team("A", gfh=int(1.5 * 19), gah=int(1.2 * 19), gfa=int(1.2 * 19), gaa=int(1.5 * 19))
    xg_home, xg_away = expected_goals(avg_home, avg_away, league)
    # ~league average (small slack for integer-goal truncation in the fixture).
    assert math.isclose(xg_home, 1.5, abs_tol=0.1)
    assert math.isclose(xg_away, 1.2, abs_tol=0.1)


def test_stronger_home_team_favoured():
    league = LeagueAverages()
    strong = _team("Strong", gfh=55, gah=10, gfa=45, gaa=15)
    weak = _team("Weak", gfh=20, gah=40, gfa=15, gaa=50)
    result = predict(strong, weak, league)
    assert result.prob_home_win > result.prob_away_win
    assert result.xg_home > result.xg_away


def test_form_adjustment_shifts_xg_up():
    league = LeagueAverages()
    base = _team("H", 40, 20, 30, 25)
    opp = _team("A", 30, 25, 25, 30)
    no_adj = expected_goals(base, opp, league)
    with_form = expected_goals(base, opp, league, Adjustments(home_form=1.08))
    assert with_form[0] > no_adj[0]


def test_top_scorelines_sorted_and_capped():
    result = predict(_team("H", 40, 18, 30, 22), _team("A", 30, 25, 24, 30), top_n=4)
    probs = [s.probability for s in result.top_scorelines]
    assert probs == sorted(probs, reverse=True)
    assert len(result.top_scorelines) == 4


def test_league_averages_from_teams_falls_back_when_empty():
    la = pm.league_averages_from_teams([])
    assert la.avg_home_goals == pm.DEFAULT_AVG_HOME_GOALS
    assert la.avg_away_goals == pm.DEFAULT_AVG_AWAY_GOALS


def test_dixon_coles_boosts_low_draws_dampens_low_wins():
    plain = score_matrix(1.4, 1.1, rho=0.0)
    dc = score_matrix(1.4, 1.1)  # default negative rho
    plain_total = sum(sum(r) for r in plain)
    dc_total = sum(sum(r) for r in dc)
    # Normalised cell comparisons: 0-0 and 1-1 up, 1-0 and 0-1 down.
    assert dc[0][0] / dc_total > plain[0][0] / plain_total
    assert dc[1][1] / dc_total > plain[1][1] / plain_total
    assert dc[1][0] / dc_total < plain[1][0] / plain_total
    assert dc[0][1] / dc_total < plain[0][1] / plain_total


def test_dixon_coles_probabilities_still_normalised():
    s = summarise_matrix(score_matrix(1.6, 1.2))
    assert math.isclose(
        s["prob_home_win"] + s["prob_draw"] + s["prob_away_win"], 1.0, abs_tol=1e-6
    )
    # draws should be a bit likelier than under plain Poisson
    s_plain = summarise_matrix(score_matrix(1.6, 1.2, rho=0.0))
    assert s["prob_draw"] > s_plain["prob_draw"]
