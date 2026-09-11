"""后台 - 表单字段动态 CRUD（项目和字段均不写死）。"""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import FormField, Project
from app.schemas.field import FieldCreate, FieldOut, FieldUpdate

router = APIRouter(tags=["字段管理"], dependencies=[Depends(get_current_user)])


def _to_out(field: FormField) -> FieldOut:
    return FieldOut.model_validate(field)


def _validate_regex(pattern: str | None) -> None:
    if pattern:
        try:
            re.compile(pattern)
        except re.error:
            raise HTTPException(status_code=422, detail="validation.pattern 不是合法的正则表达式")


@router.get(
    "/api/admin/projects/{project_id}/fields",
    response_model=list[FieldOut],
    summary="项目下的字段列表",
)
def list_fields(project_id: int, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    fields = db.scalars(
        select(FormField)
        .where(FormField.project_id == project_id)
        .order_by(FormField.sort_order, FormField.id)
    ).all()
    return [_to_out(f) for f in fields]


@router.post(
    "/api/admin/projects/{project_id}/fields",
    response_model=FieldOut,
    status_code=201,
    summary="为项目新增字段",
)
def create_field(project_id: int, payload: FieldCreate, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    _validate_regex(payload.validation.pattern if payload.validation else None)

    data = payload.model_dump()
    if payload.validation is not None:
        data["validation"] = payload.validation.model_dump(exclude_none=True)
    field = FormField(project_id=project_id, **data)
    db.add(field)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"字段键名 {payload.key} 在该项目中已存在")
    db.refresh(field)
    return _to_out(field)


@router.get("/api/admin/fields/{field_id}", response_model=FieldOut, summary="字段详情")
def get_field(field_id: int, db: Session = Depends(get_db)):
    field = db.get(FormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="字段不存在")
    return _to_out(field)


@router.put("/api/admin/fields/{field_id}", response_model=FieldOut, summary="更新字段")
def update_field(field_id: int, payload: FieldUpdate, db: Session = Depends(get_db)):
    field = db.get(FormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="字段不存在")
    _validate_regex(payload.validation.pattern if payload.validation else None)

    data = payload.model_dump(exclude_unset=True)
    if "validation" in data and payload.validation is not None:
        data["validation"] = payload.validation.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(field, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="字段键名在该项目中已存在")
    db.refresh(field)
    return _to_out(field)


@router.delete("/api/admin/fields/{field_id}", status_code=204, summary="删除字段")
def delete_field(field_id: int, db: Session = Depends(get_db)):
    field = db.get(FormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="字段不存在")
    db.delete(field)
    db.commit()
