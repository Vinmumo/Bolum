"""Predictor orchestration test — uses the offline SampleProvider, no network."""
from app.providers.sample import SampleProvider
from app.services.predictor import predict_fixture


def test_predict_fixture_end_to_end_with_sample_provider():
    provider = SampleProvider()
    result = predict_fixture(
        provider,
        home_name="Manchester City",
        away_name="Arsenal",
        league_external_id=39,
        season=2023,
        provider_name="Sample",
        db=None,
        persist=False,
    )

    assert result["home_team"]["name"] == "Manchester City"
    assert result["away_team"]["name"] == "Arsenal"

    pred = result["prediction"]
    total = pred["prob_home_win"] + pred["prob_draw"] + pred["prob_away_win"]
    assert abs(total - 1.0) < 1e-3
    assert pred["xg_home"] > 0
    assert 0 <= pred["prob_btts"] <= 1
    assert len(pred["top_scorelines"]) == 4

    # H2H summary should be populated for this canned pair.
    assert result["h2h"]["played"] > 0
    assert isinstance(result["h2h"]["summary"], str)
