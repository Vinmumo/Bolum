# Model notes — the "why"

The prediction lives in `backend/app/services/poisson_model.py` (pure maths),
with adjustments in `form_analysis.py` and `h2h_analysis.py`, orchestrated by
`predictor.py`. This doc explains the reasoning so future-you doesn't have to
reverse-engineer the weights.

## The core idea: independent Poisson

Goals in a match are modelled as two **independent Poisson random variables** —
one per team — parameterised by each side's *expected goals* (xG). This is the
classic Maher / Dixon-Coles-lite approach. It's simple, fast, explainable, and
surprisingly competitive for 1X2 / over-under / BTTS markets.

Once you have `xg_home` and `xg_away`, everything else is arithmetic on the
score matrix `P(home=i, away=j) = pmf(i; xg_home) · pmf(j; xg_away)`:

- **1X2**: sum the lower/diagonal/upper triangles.
- **Over/Under 2.5**: sum cells where `i + j > 2`.
- **BTTS**: sum cells where `i ≥ 1 and j ≥ 1`.
- **Scorelines**: the individual cells, sorted.

We truncate at 10 goals per side (`MAX_GOALS`) — beyond that the probability is
numerically negligible — and renormalise so the small truncated tail doesn't
bias the totals.

## Expected goals: attack & defence strengths

For each team we compute four strengths *relative to the league average*, split
by venue:

```
attack_home  = (team goals scored at home per game)   / league_avg_home_goals
defence_home = (team goals conceded at home per game)  / league_avg_away_goals
attack_away  = ...                                     / league_avg_away_goals
defence_away = ...                                     / league_avg_home_goals
```

A value of `1.0` is exactly average. Then:

```
xg_home = attack_home(home) · defence_away(away) · league_avg_home_goals
xg_away = attack_away(away) · defence_home(home) · league_avg_away_goals
```

Intuition: a home side's expected goals = how good their home attack is × how
leaky the opponent is away × the baseline rate for home teams. The **home/away
split matters** — home advantage is real and teams behave differently by venue,
so we never pool them.

We clamp xG to `[0.1, 6.0]` so a data glitch (e.g. a team with 1 game played)
can't produce an absurd number.

## Why the league average is a fixed baseline, not the two teams

**This is the subtle one.** You might compute the "league average" from the two
teams in the fixture. Don't — and we don't (see the comment in `predictor.py`).

If you feed two elite attacking sides (say City vs Arsenal) into a two-team
average, the "league average goals" comes out very high. Every team's *attack*
strength is then divided by that inflated baseline (looks average) while their
strong *defences* look superhuman — so xG collapses to unrealistic lows (we saw
~0.9 xG for City at home; clearly wrong).

The fix: calibrate against a **stable league baseline** (`DEFAULT_AVG_HOME_GOALS`
≈ 1.5, `DEFAULT_AVG_AWAY_GOALS` ≈ 1.2 — long-run Premier League rates). With
that, City vs Arsenal returns ~1.6 vs ~1.2 xG, which is sensible.

`league_averages_from_teams()` still exists and is correct **when given a full
set of league teams** — it's the right tool if you later fetch all 20 teams'
stats (e.g. from a standings endpoint) and want a data-driven baseline per
league. For now the fixed baseline is the pragmatic, well-behaved default.

## Adjustments: kept deliberately small

Season-long strengths carry most of the signal. Form and H2H are *nudges*, not
drivers — over-weighting them overfits noise (a 3-game hot streak, or a
6-meeting H2H sample from squads that have since changed).

### Form (`form_analysis.py`, default ±8%)

Recent results → points ratio in `[0,1]` (W=3, D=1, L=0), mapped to a multiplier
around 1.0:

```
multiplier = 1 + weight · (ratio − 0.5) · 2      # weight = 0.08
```

Perfect form → ×1.08, average → ×1.0, dire → ×0.92. Applied to that team's own
xG. No data → ratio 0.5 → no effect.

### Head-to-head (`h2h_analysis.py`, default ±5%)

From past meetings we compute each side's share of the goals scored between them.
A side that has historically outscored the other gets a small boost, capped by
the weight. Balanced history or no meetings → no effect. Weight is smaller than
form (0.05) because the sample is smaller and staler.

Both adjustments are multiplicative and combine as
`xg *= form_mult · h2h_mult`.

## Consensus across multiple APIs

When more than one provider is active, `services/aggregator.py` runs the full
pipeline **once per provider** and combines them:

- Each source produces its own expected goals + markets (shown per-source in the UI).
- The **consensus** averages the sources' expected goals (`xg_home`, `xg_away`),
  then recomputes every market from that averaged xG via `predict_from_xg` — so
  the consensus 1X2, over/under, BTTS and scorelines are all internally consistent
  (they come from one score matrix, not from separately-averaged probabilities).
- Averaging on **xG** rather than on probabilities is deliberate: xG is the model's
  natural parameter, and averaging there then recomputing avoids the mild
  incoherence you'd get from averaging already-nonlinear probabilities.
- Failed sources are skipped, not fatal.

Weighting is **equal** today. The natural upgrade to "pick the most accurate" is
to weight each source by a backtested accuracy score: keep predicting, fetch
actual results, score each provider (e.g. Brier score / log-loss on 1X2), and use
those as weights in `_consensus`. That needs a results-fetch + scoring job; the
averaging seam is already in one place to make it a small change.

## Tuning knobs

| Knob | Where | Effect |
|------|-------|--------|
| `DEFAULT_AVG_HOME/AWAY_GOALS` | `poisson_model.py` | league scoring baseline (calibration) |
| `weight` in `form_multiplier` | `form_analysis.py` | how much recent form matters |
| `weight` in `h2h_multipliers` | `h2h_analysis.py` | how much H2H matters |
| `MAX_GOALS` | `poisson_model.py` | score-matrix truncation |
| xG clamp `[0.1, 6.0]` | `expected_goals` | guards against bad data |

## Known limitations / future ideas

- **Independence assumption.** Real scores are mildly correlated (low-scoring
  draws are slightly more common than independent Poisson predicts). A
  Dixon-Coles low-score correction (a τ adjustment on the 0-0/1-0/0-1/1-1 cells)
  is the natural next step.
- **No opponent-adjusted recent form / xG-based inputs.** We use goals, not shot
  xG. If the provider exposes xG, feed that instead of goals for sharper numbers.
- **Static league baseline.** Per-league baselines (or the standings-derived
  average) would improve non-PL leagues.
- **No time decay.** All games in the season window count equally.
