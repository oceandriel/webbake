"""项目（动态创建，不写死）。"""

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 可空的英文短标识，用于公开表单 URL
    slug: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 收到客户提交时的邮件提醒开关与收件人列表（SMTP 能力由环境变量提供）
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_emails: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    fields = relationship(
        "FormField",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="FormField.sort_order",
    )
    customers = relationship(
        "Customer",
        back_populates="project",
        cascade="all, delete-orphan",
    )
