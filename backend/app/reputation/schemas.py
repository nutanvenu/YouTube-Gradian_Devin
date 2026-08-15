from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReputationClassifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=253)


class ReputationEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_kind: Literal["DOMAIN", "APP"]
    identifier: str
    verdict: Literal["KNOWN_SAFE", "KNOWN_RISK", "UNKNOWN"]
    source: str
    rationale: str
    expires_at: datetime
    bundle_version: int


class ReputationClassificationOut(BaseModel):
    identifier: str
    verdict: Literal["KNOWN_SAFE", "KNOWN_RISK", "UNKNOWN"]
    state: Literal["RESOLVED", "PENDING"]
    reason: str


class ReputationSyncOut(BaseModel):
    current_version: int
    bundle: dict[str, object] | None
    deltas: list[dict[str, object]]


class ReputationStatusOut(BaseModel):
    current_version: int
    entries: list[ReputationEntryOut]
