import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=60)
    description: str = ""
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not SLUG_PATTERN.match(v):
            raise ValueError("slug 只能包含小写字母、数字和连字符(-)，且不能以连字符开头/结尾")
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=60)
    description: str | None = None
    is_active: bool | None = None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not SLUG_PATTERN.match(v):
            raise ValueError("slug 只能包含小写字母、数字和连字符(-)，且不能以连字符开头/结尾")
        return v


class ProjectOut(BaseModel):
    id: int
    name: str
    slug: str | None = None
    description: str = ""
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
