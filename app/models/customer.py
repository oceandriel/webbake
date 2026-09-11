"""客户提交的信息：数据按字段配置校验后以 JSON 存储。"""

from sqlalchemy import JSON, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 形如 {"name": "张三", "phone": "138...", "age": 30}
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    project = relationship("Project", back_populates="customers")
