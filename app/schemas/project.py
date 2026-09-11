import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_slug(v):
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not SLUG_PATTERN.match(v):
        raise ValueError("slug 只能包含小写字母、数字和连字符(-)，且不能以连字符开头/结尾")
    return v


def normalize_emails(values):
    """收件人列表：去空白、去重、校验邮箱格式。"""
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("收件人必须是邮箱数组")
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        email = str(raw).strip()
        if not email:
            continue
        if not EMAIL_PATTERN.match(email):
            raise ValueError(f"邮箱格式不正确：{email}")
        key = email.lower()
        if key not in seen:
            seen.add(key)
            result.append(email)
    return result


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=60)
    description: str = ""
    is_active: bool = True
    notify_enabled: bool = False
    notify_emails: list[str] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v):
        return normalize_slug(v)

    @field_validator("notify_emails")
    @classmethod
    def _emails(cls, v):
        return normalize_emails(v)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=60)
    description: str | None = None
    is_active: bool | None = None
    notify_enabled: bool | None = None
    notify_emails: list[str] | None = None

    @field_validator("slug")
    @classmethod
    def _slug(cls, v):
        return normalize_slug(v)

    @field_validator("notify_emails")
    @classmethod
    def _emails(cls, v):
        return normalize_emails(v)


class ProjectOut(BaseModel):
    id: int
    name: str
    slug: str | None = None
    description: str = ""
    is_active: bool = True
    notify_enabled: bool = False
    notify_emails: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
