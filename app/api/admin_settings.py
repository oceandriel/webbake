"""后台 - 邮件提醒设置。

SMTP 凭据只能通过环境变量配置（不提供任何写入/回显接口），
这里仅返回脱敏状态供 UI 展示，并支持发送测试邮件验证连通性。
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core import email_utils
from app.models import Project

router = APIRouter(
    prefix="/api/admin/settings",
    tags=["邮件提醒"],
    dependencies=[Depends(get_current_user)],
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.get("/email", summary="邮件服务状态（脱敏）")
def email_status(db: Session = Depends(get_db)):
    configured = email_utils.smtp_configured()
    enabled_projects = db.scalars(
        select(Project)
        .where(Project.notify_enabled.is_(True))
        .order_by(Project.id)
    ).all()
    return {
        "smtp_configured": configured,
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_security": settings.smtp_security,
        "smtp_user": settings.smtp_user,
        "mail_from": settings.mail_from if configured else "",
        "enabled_projects": [
            {"id": p.id, "name": p.name, "notify_emails": p.notify_emails or []}
            for p in enabled_projects
        ],
    }


class TestEmailIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)


@router.post("/email/test", summary="发送测试邮件（同步返回 SMTP 结果）")
def send_test_email(payload: TestEmailIn):
    if not EMAIL_PATTERN.match(payload.email.strip()):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    if not email_utils.smtp_configured():
        raise HTTPException(
            status_code=400,
            detail="SMTP 尚未配置：请在服务器环境变量中设置 SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD 等后重启服务",
        )
    html_body = (
        '<p style="font-family:sans-serif">这是一封来自'
        f"<b>{settings.app_name}</b>的测试邮件。</p>"
        '<p style="color:#6b7280;font-size:13px">收到此邮件说明 SMTP 配置正确，'
        "客户提交表单的邮件提醒可以正常发送。</p>"
    )
    text_body = f"这是一封来自{settings.app_name}的测试邮件，收到说明 SMTP 配置正确。"
    try:
        email_utils.send_email(
            [payload.email.strip()], "【测试】SMTP 配置验证", html_body, text_body
        )
    except Exception as exc:  # SMTP/认证/网络错误直接反馈给操作者
        raise HTTPException(status_code=502, detail=f"测试邮件发送失败：{exc}")
    return {"ok": True, "message": f"测试邮件已发送至 {payload.email.strip()}"}
