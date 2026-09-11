from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class CustomerUpdate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class CustomerOut(BaseModel):
    id: int
    project_id: int
    data: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublicSubmissionIn(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
