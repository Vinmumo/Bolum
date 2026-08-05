from app.services import h2h_analysis as h


def _matches():
    # team 1 (id=1) vs team 2 (id=2): mixed venues
    return [
        h.H2HMatch(home_team_id=1, away_team_id=2, home_goals=2, away_goals=0),
        h.H2HMatch(home_team_id=2, away_team_id=1, home_goals=1, away_goals=1),
        h.H2HMatch(home_team_id=1, away_team_id=2, home_goals=3, away_goals=2),
    ]


def test_summary_counts_from_team1_perspective():
    s = h.summarise(_matches(), team1_id=1, team2_id=2)
    assert s.played == 3
    assert s.team1_wins == 2  # 2-0 and 3-2
    assert s.draws == 1  # 1-1
    assert s.team2_wins == 0
    assert s.team1_goals == 2 + 1 + 3
    assert s.team2_goals == 0 + 1 + 2


def test_empty_h2h_has_neutral_multipliers():
    s = h.summarise([], team1_id=1, team2_id=2)
    assert s.played == 0
    assert h.h2h_multipliers(s) == (1.0, 1.0)


def test_dominant_team_gets_boost():
    s = h.summarise(_matches(), team1_id=1, team2_id=2)
    m1, m2 = h.h2h_multipliers(s, weight=0.05)
    assert m1 > 1.0  # team1 outscored team2
    assert m2 < 1.0
