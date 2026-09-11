"""根据后端字段配置动态校验客户提交的数据。

字段配置不是写死的：运行时从数据库读取 FormField 列表，
本模块按每个字段的 type / required / options / validation 进行校验与类型转换。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_MISSING = object()


class SubmissionError(Exception):
    """校验失败：errors 为 {字段key: 错误消息}。"""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def validate_submission(fields: list, data: Any) -> dict[str, Any]:
    """根据字段定义校验并返回清洗后的数据。

    - 未在字段配置中定义的键会被丢弃；
    - 必填缺失 / 类型不符 / 选项越界等收集为 SubmissionError。
    """
    if not isinstance(data, dict):
        raise SubmissionError({"_": "提交内容必须是 JSON 对象，例如 {\"name\": \"张三\"}"})

    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    for field in fields:
        key = field.key
        ftype = field.type
        value = data.get(key, _MISSING)

        if value is _MISSING or _is_empty(value):
            if field.required:
                errors[key] = "该字段为必填项"
            continue

        rules = field.validation or {}
        options = field.options or []

        try:
            cleaned[key] = _validate_value(ftype, value, rules, options)
        except ValueError as exc:
            errors[key] = str(exc)

    if errors:
        raise SubmissionError(errors)
    return cleaned


def _validate_value(ftype: str, value: Any, rules: dict, options: list) -> Any:
    if ftype in ("text", "textarea", "phone"):
        if not isinstance(value, str):
            raise ValueError("必须是文本")
        return _check_string(value, rules, email=False)

    if ftype == "email":
        if not isinstance(value, str):
            raise ValueError("必须是邮箱字符串")
        value = value.strip()
        if not EMAIL_RE.match(value):
            raise ValueError("邮箱格式不正确")
        return _check_string(value, rules, email=True)

    if ftype == "number":
        return _check_number(value, rules)

    if ftype == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "1", "yes", "on", "是"):
                return True
            if low in ("false", "0", "no", "off", "否"):
                return False
        raise ValueError("必须是布尔值（true/false）")

    if ftype == "date":
        if not isinstance(value, str):
            raise ValueError("日期必须是 YYYY-MM-DD 字符串")
        try:
            date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("日期格式不正确，应为 YYYY-MM-DD")
        return value.strip()

    if ftype == "datetime":
        if not isinstance(value, str):
            raise ValueError("日期时间必须是 ISO 8601 字符串")
        text = value.strip().replace("Z", "+00:00")
        try:
            datetime.fromisoformat(text)
        except ValueError:
            raise ValueError("日期时间格式不正确，应为 YYYY-MM-DDTHH:MM:SS")
        return value.strip()

    if ftype in ("select", "radio"):
        text = str(value).strip()
        if text not in options:
            raise ValueError("必须从给定选项中选择")
        return text

    if ftype == "multiselect":
        if not isinstance(value, list):
            raise ValueError("多选字段必须提交数组")
        result = [str(v).strip() for v in value]
        invalid = [v for v in result if v not in options]
        if invalid:
            raise ValueError(f"包含无效选项: {', '.join(invalid)}")
        return result

    raise ValueError(f"不支持的字段类型: {ftype}")


def _check_string(value: str, rules: dict, email: bool = False) -> str:
    min_length = rules.get("min_length")
    max_length = rules.get("max_length")
    pattern = rules.get("pattern")
    if min_length is not None and len(value) < min_length:
        raise ValueError(f"长度不能少于 {min_length} 个字符")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"长度不能超过 {max_length} 个字符")
    if pattern:
        try:
            if not re.search(pattern, value):
                raise ValueError("格式不符合规则")
        except re.error:
            raise ValueError("字段正则规则配置有误")
    return value


def _check_number(value: Any, rules: dict) -> int | float:
    if isinstance(value, bool):
        raise ValueError("必须是数字")
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        number = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            number = int(text)
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                raise ValueError("必须是数字")
    else:
        raise ValueError("必须是数字")

    minimum = rules.get("min")
    maximum = rules.get("max")
    if minimum is not None and number < minimum:
        raise ValueError(f"不能小于 {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"不能大于 {maximum}")
    return number
