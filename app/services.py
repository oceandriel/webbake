"""业务服务层：路由共用的项目解析、字段读取、客户数据写入逻辑。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.validation import validate_submission
from app.models import Customer, FormField, Project


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def resolve_public_project(db: Session, id_or_slug: str) -> Project:
    """公开表单按数字 id 或 slug 定位项目。"""
    from fastapi import HTTPException

    query = select(Project)
    if id_or_slug.isdigit():
        project = db.get(Project, int(id_or_slug))
    else:
        project = db.scalar(query.where(Project.slug == id_or_slug))
    if project is None or not project.is_active:
        raise HTTPException(status_code=404, detail="项目不存在或已停用")
    return project


def active_fields(db: Session, project_id: int) -> list[FormField]:
    stmt = (
        select(FormField)
        .where(FormField.project_id == project_id, FormField.is_active.is_(True))
        .order_by(FormField.sort_order, FormField.id)
    )
    return list(db.scalars(stmt).all())


def create_customer(db: Session, project_id: int, payload: dict) -> Customer:
    project = get_project_or_404(db, project_id)
    fields = active_fields(db, project_id)
    cleaned = validate_submission(fields, payload)
    customer = Customer(project_id=project_id, data=cleaned)
    db.add(customer)
    # 先落库再通知，避免“通知已发但数据没存”的不一致
    db.commit()
    db.refresh(customer)
    _maybe_notify_submission(project, fields, customer)
    return customer


def _maybe_notify_submission(project: Project, fields: list[FormField], customer: Customer) -> None:
    """按项目配置异步发送邮件提醒；任何异常都不得影响提交结果。"""
    try:
        from app.core import email_utils

        if not (project.notify_enabled and project.notify_emails and email_utils.smtp_configured()):
            return

        rows = [(field.label, customer.data.get(field.key)) for field in fields]
        submitted_at = customer.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        email_utils.notify_submission(
            project_name=project.name,
            recipients=list(project.notify_emails),
            rows=rows,
            submitted_at=submitted_at,
        )
    except Exception:  # noqa: BLE001 - 通知失败仅记录日志
        import logging

        logging.getLogger("cims.mail").exception("触发提交提醒失败，已忽略（不影响客户提交）")


def update_customer(db: Session, customer: Customer, payload: dict) -> Customer:
    # 全量替换：按当前字段配置重新校验
    cleaned = validate_submission(active_fields(db, customer.project_id), payload)
    customer.data = cleaned
    db.commit()
    db.refresh(customer)
    return customer
