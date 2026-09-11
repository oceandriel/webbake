"""邮件提醒：SMTP 发送 + 后台线程异步执行。

设计要点：
- SMTP 凭据全部来自环境变量，模块不提供任何凭据写入接口；
- 通知属于“副作用”，客户表单提交链路只投递任务，绝不因 SMTP 故障而失败；
- send_email() 为阻塞实现（供“发送测试邮件”同步调用），
  notify_submission() 通过线程池异步执行，异常仅记录日志。
"""

from __future__ import annotations

import html
import logging
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any, Iterable

from app.config import settings

logger = logging.getLogger("cims.mail")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")


def smtp_configured() -> bool:
    return settings.smtp_configured


def send_email(to_addrs: Iterable[str], subject: str, html_body: str, text_body: str) -> None:
    """同步发送邮件。SMTP 不可用或发送失败时抛出异常。"""
    if not smtp_configured():
        raise RuntimeError("尚未配置 SMTP（需要设置 SMTP_HOST / SMTP_USER 等环境变量）")

    recipients = [a.strip() for a in to_addrs if a and a.strip()]
    if not recipients:
        raise ValueError("收件人不能为空")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.app_name, settings.mail_from))
    msg["To"] = ", ".join(recipients)
    msg["Message-ID"] = make_msgid()
    msg.set_content(text_body, subtype="plain", charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")

    security = (settings.smtp_security or "starttls").lower()
    if security == "ssl":
        client = smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout
        )
    else:
        client = smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout
        )

    try:
        if security == "starttls":
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if settings.smtp_password:
            client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(msg)
    finally:
        try:
            client.quit()
        except Exception:
            client.close()


def display_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, list):
        return "、".join(str(v) for v in value)
    return str(value)


def build_submission_email(
    project_name: str,
    rows: list[tuple[str, Any]],
    submitted_at: str,
) -> tuple[str, str]:
    """根据字段标签与客户提交值构造 (html, text) 邮件正文。"""
    title = f"【新客户提交】{project_name}"

    lines = [title, f"提交时间：{submitted_at}", ""]
    for label, value in rows:
        lines.append(f"{label}：{display_value(value)}")
    text_body = "\n".join(lines)

    trs = "".join(
        "<tr>"
        f'<td style="padding:8px 12px;background:#f9fafb;font-weight:600;white-space:nowrap;'
        f'border:1px solid #e5e7eb">{html.escape(label)}</td>'
        f'<td style="padding:8px 12px;border:1px solid #e5e7eb">{html.escape(display_value(value))}</td>'
        "</tr>"
        for label, value in rows
    )
    html_body = f"""\
<!doctype html>
<html lang="zh-CN"><body style="margin:0;padding:24px;background:#f3f4f6;font-family:'Microsoft YaHei',sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden">
    <div style="background:#4f46e5;color:#fff;padding:16px 22px;font-size:16px;font-weight:700">
      新客户表单提交提醒
    </div>
    <div style="padding:22px">
      <p style="margin:0 0 4px">项目：<b>{html.escape(project_name)}</b></p>
      <p style="margin:0 0 16px;color:#6b7280;font-size:13px">提交时间：{html.escape(submitted_at)}</p>
      <table style="border-collapse:collapse;width:100%;font-size:14px">{trs}</table>
      <p style="color:#9ca3af;font-size:12px;margin:18px 0 0">此邮件由系统自动发送，请勿直接回复。</p>
    </div>
  </div>
</body></html>"""
    return html_body, text_body


def notify_submission(
    project_name: str,
    recipients: list[str],
    rows: list[tuple[str, Any]],
    submitted_at: str,
) -> None:
    """异步投递“新客户提交”提醒邮件；任何异常都只记录日志。"""
    if not recipients:
        return

    def _job() -> None:
        try:
            html_body, text_body = build_submission_email(project_name, rows, submitted_at)
            send_email(recipients, f"【新客户提交】{project_name}", html_body, text_body)
            logger.info("提交提醒邮件已发送至 %s（项目=%s）", recipients, project_name)
        except Exception:
            logger.exception("提交提醒邮件发送失败（项目=%s, 收件人=%s）", project_name, recipients)

    _executor.submit(_job)
