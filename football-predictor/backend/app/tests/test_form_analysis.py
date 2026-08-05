import math

from app.services import form_analysis as fa


def test_points_ratio_extremes():
    assert fa.form_points_ratio(["W", "W", "W"]) == 1.0
    assert fa.form_points_ratio(["L", "L", "L"]) == 0.0
    assert fa.form_points_ratio([]) == 0.5  # no data -> neutral


def test_multiplier_neutral_for_average_form():
    # 1 win, 1 draw, 1 loss = 4/9 ~ below average but close; use balanced set
    assert math.isclose(fa.form_multiplier(["W", "L"]), 1.0, abs_tol=1e-9)


def test_multiplier_bounds():
    hot = fa.form_multiplier(["W", "W", "W", "W", "W"], weight=0.08)
    cold = fa.form_multiplier(["L", "L", "L", "L", "L"], weight=0.08)
    assert math.isclose(hot, 1.08, abs_tol=1e-9)
    assert math.isclose(cold, 0.92, abs_tol=1e-9)
