"""表单字段定义（项目下动态增删改查，前端据此自动生成表单）。"""

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

# 支持的字段类型
FIELD_TYPES = (
    "text",        # 单行文本
    "textarea",    # 多行文本
    "number",      # 数字
    "email",       # 邮箱
    "phone",       # 电话
    "date",        # 日期
    "datetime",    # 日期时间
    "select",      # 下拉单选
    "radio",       # 单选
    "multiselect", # 多选
    "boolean",     # 是/否
)


class FormField(Base, TimestampMixin):
    __tablename__ = "fields"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_field_project_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # 字段在提交数据 JSON 中的键名，如 name / phone
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # select / radio / multiselect 的可选项
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    placeholder: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    default_value: Mapped[object | None] = mapped_column(JSON, nullable=True)
    # 额外校验规则：{min, max, min_length, max_length, pattern}
    validation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    project = relationship("Project", back_populates="fields")
