"""Provider admin schemas. API keys go IN but never come back out in full."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str
    provider_type: str = Field(..., description="e.g. 'api_football' or 'sample'.")
    base_url: str
    auth_header: str = "x-apisports-key"
    api_key: str | None = Field(None, description="Stored encrypted; never returned.")
    active: bool = True
    priority: int = Field(100, description="Lower = preferred; lowest active serves fixtures.")
    weight: float = Field(1.0, description="Consensus weight; 1.0 = equal say.")


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    auth_header: str | None = None
    api_key: str | None = Field(None, description="Send to rotate the key.")
    active: bool | None = None
    priority: int | None = None
    weight: float | None = None


class ProviderOut(BaseModel):
    id: int
    name: str
    provider_type: str
    base_url: str
    auth_header: str
    api_key_masked: str  # e.g. "********abcd" — never the full key
    has_key: bool
    active: bool
    priority: int
    weight: float

    model_config = {"from_attributes": True}
