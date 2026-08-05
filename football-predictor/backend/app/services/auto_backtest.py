"""Automatic gameweek replays.

A background loop (started from main.py's lifespan) that periodically finds
gameweeks which have FINISHED but were never backtested, and replays them. So
during the season, accuracy accumulates on its own — no clicking.

Quota-friendly by design:
- runs every AUTO_BACKTEST_INTERVAL_HOURS (default 12),
- replays at most AUTO_BACKTEST_MAX_PER_RUN gameweeks per cycle (default 4),
- a gameweek costs ~2 throttled provider calls (matches + standings), both cached,
- before the season starts (no finished rounds) it's a no-op.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.backtest import BacktestResult
from app.models.league import League
from app.providers.registry import ProviderRegistry
from app.services.backtest import replay_gameweek

logger = logging.getLogger("football_predictor.auto_backtest")


def run_pending_backtests(max_per_run: int | None = None) -> list[dict]:
    """Replay up to `max_per_run` finished-but-unreplayed gameweeks.

    Covers every active league's current season. Returns a small report list.
    Synchronous — call via asyncio.to_thread from async contexts.
    """
    limit = max_per_run or settings.auto_backtest_max_per_run
    report: list[dict] = []
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        registry = ProviderRegistry(db)
        try:
            provider = registry.get_active_provider()
        except Exception as exc:
            logger.warning("auto-backtest: no provider (%s)", exc)
            return report

        leagues = db.execute(
            select(League).where(League.active.is_(True))
        ).scalars().all()

        for league in leagues:
            if len(report) >= limit:
                break
            try:
                rounds = provider.get_rounds(league.external_provider_id, league.season)
            except Exception as exc:
                logger.warning("auto-backtest: rounds failed for %s (%s)", league.name, exc)
                continue

            done_mds = {
                md for (md,) in db.execute(
                    select(BacktestResult.matchday).where(
                        BacktestResult.league_id == league.external_provider_id,
                        BacktestResult.season == league.season,
                    ).distinct()
                )
            }

            for r in rounds:
                if len(report) >= limit:
                    break
                md = _matchday_number(r.name)
                if md is None or md in done_mds:
                    continue
                end = _parse_dt(r.end_date)
                if end is None or end >= now:
                    continue  # not finished yet
                try:
                    payload = replay_gameweek(
                        provider, db,
                        league_external_id=league.external_provider_id,
                        season=league.season, matchday=md,
                    )
                    report.append(
                        {
                            "league": league.name,
                            "season": league.season,
                            "matchday": md,
                            "fixtures": len(payload["fixtures"]),
                        }
                    )
                    logger.info(
                        "auto-backtest: replayed %s season %s MD%s (%s fixtures)",
                        league.name, league.season, md, len(payload["fixtures"]),
                    )
                except Exception as exc:
                    logger.warning("auto-backtest: MD%s failed (%s)", md, exc)
    return report


async def auto_backtest_loop() -> None:
    """Forever-loop for the app lifespan. First run shortly after boot."""
    await asyncio.sleep(60)  # let startup settle
    while True:
        try:
            await asyncio.to_thread(run_pending_backtests)
        except Exception:  # never let the loop die
            logger.exception("auto-backtest cycle failed")
        await asyncio.sleep(settings.auto_backtest_interval_hours * 3600)


def _matchday_number(round_name: str | None) -> int | None:
    if not round_name:
        return None
    import re

    m = re.search(r"(\d+)", round_name)
    return int(m.group(1)) if m else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
