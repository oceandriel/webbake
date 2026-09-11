import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

FieldType = Literal[
    "text", "textarea", "number", "email", "phone",
    "date", "datetime", "select", "radio", "multiselect", "boolean",
]

KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
CHOICE_TYPES = {"select", "radio", "multiselect"}
STRING_TYPES = {"text", "textarea", "email", "phone"}
NUMBER_TYPES = {"number"}


class FieldValidationRule(BaseModel):
    min: float | None = None
    max: float | None = None
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)
    pattern: str | None = None


def _check_key(v: str) -> str:
    v = v.strip()
    if not KEY_PATTERN.match(v):
        raise ValueError("字段键名只能包含字母、数字、下划线，且以字母或下划线开头")
    return v


def _check_options(options, field_type: str) -> list[str] | None:
    if field_type in CHOICE_TYPES:
        if not options or not isinstance(options, list):
            raise ValueError("select/radio/multiselect 类型必须提供非空选项列表")
        options = [str(o).strip() for o in options if str(o).strip()]
        if not options:
            raise ValueError("选项不能为空字符串")
        return options
    return options


class FieldCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=64)
    type: FieldType
    required: bool = False
    options: list[str] | None = None
    placeholder: str = ""
    default_value: Any | None = None
    validation: FieldValidationRule | None = None
    description: str = ""
    sort_order: int = 0
    is_active: bool = True

    @field_validator("key")
    @classmethod
    def check_key(cls, v):
        return _check_key(v)

    @field_validator("options")
    @classmethod
    def check_options(cls, v, info):
        return _check_options(v, info.data.get("type", ""))


class FieldUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    key: str | None = Field(default=None, min_length=1, max_length=64)
    type: FieldType | None = None
    required: bool | None = None
    options: list[str] | None = None
    placeholder: str | None = None
    default_value: Any | None = None
    validation: FieldValidationRule | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None

    @field_validator("key")
    @classmethod
    def check_key(cls, v):
        return None if v is None else _check_key(v)


class FieldOut(BaseModel):
    id: int
    project_id: int
    label: str
    key: str
    type: str
    required: bool
    options: list[str] | None = None
    placeholder: str = ""
    default_value: Any | None = None
    validation: dict[str, Any] | None = None
    description: str = ""
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
