"""Admin router — single user, JWT-protected. Provider/league CRUD + usage."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.core.security import create_access_token, encrypt_secret, mask_key, decrypt_secret
from app.db.session import get_db
from app.models.api_usage_log import ApiUsageLog
from app.models.league import League
from app.models.prediction import Prediction
from app.models.provider import Provider
from app.providers.registry import PROVIDER_CLASSES
from app.schemas.auth import ApiUsageSummary, TokenResponse
from app.schemas.league import LeagueCreate, LeagueOut, LeagueUpdate
from app.schemas.prediction import RecentPredictionOut
from app.schemas.provider import ProviderCreate, ProviderOut, ProviderUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    ok_user = secrets.compare_digest(form.username, settings.admin_username)
    ok_pass = secrets.compare_digest(form.password, settings.admin_password)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad admin credentials."
        )
    return TokenResponse(access_token=create_access_token(subject=settings.admin_username))


@router.get("/me")
def me(admin: str = Depends(require_admin)):
    return {"username": admin}


@router.get("/provider-types")
def provider_types(_: str = Depends(require_admin)):
    return {"types": sorted(PROVIDER_CLASSES.keys())}


# --------------------------------------------------------------------------- #
# Provider CRUD
# --------------------------------------------------------------------------- #
def _provider_out(p: Provider) -> ProviderOut:
    key = decrypt_secret(p.encrypted_api_key) if p.encrypted_api_key else None
    return ProviderOut(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        base_url=p.base_url,
        auth_header=p.auth_header,
        api_key_masked=mask_key(key),
        has_key=bool(p.encrypted_api_key),
        active=p.active,
    )


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(_: str = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Provider).order_by(Provider.id)).scalars().all()
    return [_provider_out(p) for p in rows]


@router.post("/providers", response_model=ProviderOut, status_code=201)
def create_provider(
    body: ProviderCreate, _: str = Depends(require_admin), db: Session = Depends(get_db)
):
    if body.provider_type not in PROVIDER_CLASSES:
        raise HTTPException(400, f"Unknown provider_type. Known: {sorted(PROVIDER_CLASSES)}")
    p = Provider(
        name=body.name,
        provider_type=body.provider_type,
        base_url=body.base_url,
        auth_header=body.auth_header,
        encrypted_api_key=encrypt_secret(body.api_key) if body.api_key else None,
        active=body.active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _provider_out(p)


@router.put("/providers/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "Provider not found.")
    if body.name is not None:
        p.name = body.name
    if body.provider_type is not None:
        if body.provider_type not in PROVIDER_CLASSES:
            raise HTTPException(400, "Unknown provider_type.")
        p.provider_type = body.provider_type
    if body.base_url is not None:
        p.base_url = body.base_url
    if body.auth_header is not None:
        p.auth_header = body.auth_header
    if body.api_key is not None:
        p.encrypted_api_key = encrypt_secret(body.api_key) if body.api_key else None
    if body.active is not None:
        p.active = body.active
    db.commit()
    db.refresh(p)
    return _provider_out(p)


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(
    provider_id: int, _: str = Depends(require_admin), db: Session = Depends(get_db)
):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "Provider not found.")
    db.delete(p)
    db.commit()


# --------------------------------------------------------------------------- #
# League CRUD
# --------------------------------------------------------------------------- #
@router.get("/leagues", response_model=list[LeagueOut])
def admin_list_leagues(_: str = Depends(require_admin), db: Session = Depends(get_db)):
    return db.execute(select(League).order_by(League.id)).scalars().all()


@router.post("/leagues", response_model=LeagueOut, status_code=201)
def create_league(
    body: LeagueCreate, _: str = Depends(require_admin), db: Session = Depends(get_db)
):
    lg = League(**body.model_dump())
    db.add(lg)
    db.commit()
    db.refresh(lg)
    return lg


@router.put("/leagues/{league_id}", response_model=LeagueOut)
def update_league(
    league_id: int,
    body: LeagueUpdate,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    lg = db.get(League, league_id)
    if not lg:
        raise HTTPException(404, "League not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lg, field, value)
    db.commit()
    db.refresh(lg)
    return lg


@router.delete("/leagues/{league_id}", status_code=204)
def delete_league(
    league_id: int, _: str = Depends(require_admin), db: Session = Depends(get_db)
):
    lg = db.get(League, league_id)
    if not lg:
        raise HTTPException(404, "League not found.")
    db.delete(lg)
    db.commit()


# --------------------------------------------------------------------------- #
# Usage logs + recent predictions
# --------------------------------------------------------------------------- #
@router.get("/usage", response_model=list[ApiUsageSummary])
def usage_summary(_: str = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Provider.id,
            Provider.name,
            func.count(ApiUsageLog.id),
            func.sum(cast(ApiUsageLog.success, Integer)),
        )
        .select_from(Provider)
        .join(ApiUsageLog, ApiUsageLog.provider_id == Provider.id, isouter=True)
        .group_by(Provider.id, Provider.name)
    ).all()
    out = []
    for pid, name, total, successful in rows:
        total = total or 0
        successful = successful or 0
        out.append(
            ApiUsageSummary(
                provider_id=pid,
                provider_name=name,
                total_calls=total,
                successful=successful,
                failed=total - successful,
            )
        )
    return out


@router.get("/predictions", response_model=list[RecentPredictionOut])
def admin_recent_predictions(
    limit: int = 50, _: str = Depends(require_admin), db: Session = Depends(get_db)
):
    rows = db.execute(
        select(Prediction).order_by(Prediction.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        RecentPredictionOut(
            id=r.id,
            home_team=r.home_team,
            away_team=r.away_team,
            xg_home=r.xg_home,
            xg_away=r.xg_away,
            prob_home=r.prob_home,
            prob_draw=r.prob_draw,
            prob_away=r.prob_away,
            provider_name=r.provider_name,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
