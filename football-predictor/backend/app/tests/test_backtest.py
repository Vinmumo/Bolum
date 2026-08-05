"""Multi-line O/U output + backtest scoring logic (pure parts)."""
import math

from app.providers.base import ProviderFixture, ProviderTeam, ProviderTeamStats
from app.services.backtest import _score_fixture
from app.services.poisson_model import GOAL_LINES, predict_from_xg


def test_over_lines_are_monotonic_and_consistent():
    r = predict_from_xg(1.5, 1.2)
    lines = r.over_lines
    assert set(lines) == {f"{line}" for line in GOAL_LINES}
    # P(over 1.5) >= P(over 2.5) >= P(over 3.5), and 2.5 matches the legacy field
    assert lines["1.5"] >= lines["2.5"] >= lines["3.5"]
    assert math.isclose(lines["2.5"], r.prob_over_2_5, abs_tol=1e-9)
    # expected total ~ xg_home + xg_away
    assert math.isclose(r.expected_total_goals, 2.7, abs_tol=0.05)


def _stats(team_id, name, gfh, gah, gfa, gaa):
    return ProviderTeamStats(
        team_id=team_id, name=name, games_home=19, games_away=19,
        goals_for_home=gfh, goals_against_home=gah,
        goals_for_away=gfa, goals_against_away=gaa,
    )


def _fixture(home_goals, away_goals):
    return ProviderFixture(
        id=1, league_id=39, season=2025, round="Gameweek 20", date=None,
        status="FINISHED",
        home=ProviderTeam(id=1, name="Home"),
        away=ProviderTeam(id=2, name="Away"),
        home_goals=home_goals, away_goals=away_goals,
    )


def test_score_fixture_marks_hits_correctly():
    home = _stats(1, "Home", 50, 15, 40, 20)  # strong attack both venues
    away = _stats(2, "Away", 45, 18, 38, 22)
    row = _score_fixture(
        _fixture(3, 2),  # 5 goals: over on every line
        home, away, league_external_id=39, season=2025, matchday=20,
    )
    for line in GOAL_LINES:
        e = row.lines[f"{line}"]
        assert e["actual"] == "over"
        assert e["hit"] == (e["pick"] == "over")
        assert 0.0 <= e["p_over"] <= 1.0
    assert row.result_1x2["actual"] == "home"
    assert row.result_1x2["pick"] in ("home", "draw", "away")


def test_score_fixture_under_case():
    home = _stats(1, "Home", 20, 12, 15, 14)  # low-scoring sides
    away = _stats(2, "Away", 18, 13, 14, 15)
    row = _score_fixture(
        _fixture(0, 0), home, away, league_external_id=39, season=2025, matchday=20,
    )
    for line in GOAL_LINES:
        assert row.lines[f"{line}"]["actual"] == "under"
    assert row.result_1x2["actual"] == "draw"
