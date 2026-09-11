"""公开表单接口（无需鉴权）：前端据此自动生成表单并提交客户信息。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.validation import SubmissionError
from app.schemas.customer import CustomerOut, PublicSubmissionIn
from app.schemas.field import FieldOut
from app.services import active_fields, create_customer, resolve_public_project

router = APIRouter(prefix="/api/public", tags=["公开表单"])


@router.get("/projects", summary="启用中的项目列表（用于选择填报项目）")
def list_public_projects(db: Session = Depends(get_db)):
    from sqlalchemy import select

    from app.models import Project

    rows = db.scalars(
        select(Project).where(Project.is_active.is_(True)).order_by(Project.id.desc())
    ).all()
    return [
        {"id": p.id, "name": p.name, "slug": p.slug, "description": p.description}
        for p in rows
    ]


@router.get("/projects/{id_or_slug}/form", summary="获取项目的动态表单配置")
def get_form(id_or_slug: str, db: Session = Depends(get_db)):
    project = resolve_public_project(db, id_or_slug)
    fields = active_fields(db, project.id)
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "description": project.description,
        },
        "fields": [FieldOut.model_validate(f).model_dump() for f in fields],
    }


@router.post(
    "/projects/{id_or_slug}/submissions",
    response_model=CustomerOut,
    status_code=201,
    summary="提交客户信息（按字段配置动态校验后入库）",
)
def submit_form(id_or_slug: str, payload: PublicSubmissionIn, db: Session = Depends(get_db)):
    project = resolve_public_project(db, id_or_slug)
    try:
        return create_customer(db, project.id, payload.data)
    except SubmissionError as exc:
        # 422 detail 为 {字段key: 消息}，前端可逐字段提示
        raise HTTPException(status_code=422, detail=exc.errors)
