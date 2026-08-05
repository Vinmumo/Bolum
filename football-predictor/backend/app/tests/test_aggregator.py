"""Consensus aggregator: averaging across providers + graceful skip."""
import math

import pytest

from app.providers.base import (
    FootballDataProvider,
    ProviderError,
    ProviderH2HMatch,
    ProviderTeam,
    ProviderTeamStats,
)
from app.services.aggregator import predict_fixture_consensus
from app.services.poisson_model import predict_from_xg


class _FakeProvider(FootballDataProvider):
    """Two teams with configurable goal output, so we can steer xG per source."""

    def __init__(self, gf_home: int):
        self._gf_home = gf_home

    def get_team(self, name, league_id=None, season=None):
        tid = 1 if "home" in name.lower() else 2
        return ProviderTeam(id=tid, name=name)

    def get_team_stats(self, team_id, season, league_id):
        # Home team's home scoring depends on gf_home; everything else fixed.
        gf_home = self._gf_home if team_id == 1 else 30
        return ProviderTeamStats(
            team_id=team_id, name=f"Team {team_id}",
            games_home=19, games_away=19,
            goals_for_home=gf_home, goals_against_home=20,
            goals_for_away=25, goals_against_away=25,
        )

    def get_h2h(self, team1_id, team2_id, limit=10):
        return []

    def get_fixtures(self, league_id, season, round=None):
        return []

    def get_leagues(self):
        return []


class _BrokenProvider(_FakeProvider):
    def get_team(self, name, league_id=None, season=None):
        raise ProviderError("boom")


def _predict(providers):
    return predict_fixture_consensus(
        providers, home_name="home", away_name="away",
        league_external_id=39, season=2023, db=None, persist=False,
    )


def test_predict_from_xg_matches_predict_pipeline():
    r = predict_from_xg(1.5, 1.2)
    total = r.prob_home_win + r.prob_draw + r.prob_away_win
    assert math.isclose(total, 1.0, abs_tol=1e-6)
    assert r.xg_home == 1.5 and r.xg_away == 1.2


def test_consensus_is_average_of_sources():
    low = _FakeProvider(gf_home=30)   # weaker home attack -> lower xg_home
    high = _FakeProvider(gf_home=60)  # stronger -> higher xg_home
    res_low = _predict([("low", low)])
    res_high = _predict([("high", high)])
    res_both = _predict([("low", low), ("high", high)])

    xg_low = res_low["consensus"]["xg_home"]
    xg_high = res_high["consensus"]["xg_home"]
    xg_both = res_both["consensus"]["xg_home"]

    assert xg_low < xg_both < xg_high
    assert math.isclose(xg_both, (xg_low + xg_high) / 2, abs_tol=0.02)
    assert res_both["meta"]["source_count"] == 2
    assert len(res_both["sources"]) == 2


def test_failing_provider_is_skipped_not_fatal():
    good = _FakeProvider(gf_home=45)
    bad = _BrokenProvider(gf_home=45)
    res = _predict([("good", good), ("bad", bad)])
    assert res["meta"]["providers_used"] == ["good"]
    assert res["meta"]["providers_failed"][0]["provider"] == "bad"
    assert res["meta"]["source_count"] == 1


def test_all_providers_failing_raises():
    with pytest.raises(ProviderError):
        _predict([("bad", _BrokenProvider(gf_home=45))])


def test_weighted_consensus_leans_toward_heavier_source():
    low = _FakeProvider(gf_home=30)
    high = _FakeProvider(gf_home=60)
    equal = _predict([("low", low, 1.0), ("high", high, 1.0)])
    heavy_high = _predict([("low", low, 1.0), ("high", high, 3.0)])
    assert heavy_high["consensus"]["xg_home"] > equal["consensus"]["xg_home"]
    # weights surface in the sources payload
    assert heavy_high["sources"][1]["weight"] == 3.0
