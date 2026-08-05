"""Admin auth schemas."""
from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiUsageOut(BaseModel):
    id: int
    provider_id: int
    endpoint: str
    status_code: int | None
    success: bool
    created_at: str


class ApiUsageSummary(BaseModel):
    provider_id: int
    provider_name: str
    total_calls: int
    successful: int
    failed: int
