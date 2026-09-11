"""外部集成 API（解耦前端使用）：通过环境变量 API_TOKEN 鉴权。

请求头：X-API-Token: <环境变量 API_TOKEN 的值>
更换 Token 只需修改环境变量并重启，无需任何 UI 操作。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_db, require_api_token
from app.core.validation import SubmissionError
from app.models import Customer, FormField, Project
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.schemas.field import FieldOut
from app.schemas.project import ProjectOut
from app.services import create_customer, get_project_or_404, update_customer

router = APIRouter(
    prefix="/api/v1",
    tags=["集成API（API Token）"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/projects", response_model=Page[ProjectOut], summary="项目列表")
def list_projects(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
    stmt = db.query(Project).order_by(Project.id.desc())
    total = stmt.count()
    rows = stmt.offset(pagination.offset).limit(pagination.page_size).all()
    return Page[ProjectOut](
        items=[ProjectOut.model_validate(p) for p in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/projects/{project_id}/fields", response_model=list[FieldOut], summary="项目字段配置")
def list_fields(project_id: int, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    rows = (
        db.query(FormField)
        .filter(FormField.project_id == project_id)
        .order_by(FormField.sort_order, FormField.id)
        .all()
    )
    return [FieldOut.model_validate(f) for f in rows]


@router.get(
    "/projects/{project_id}/customers",
    response_model=Page[CustomerOut],
    summary="客户信息列表",
)
def list_customers(
    project_id: int,
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    get_project_or_404(db, project_id)
    stmt = db.query(Customer).filter(Customer.project_id == project_id)
    if q:
        stmt = stmt.filter(text("data LIKE :pattern")).params(pattern=f"%{q}%")
    total = stmt.count()
    rows = stmt.order_by(Customer.id.desc()).offset(pagination.offset).limit(pagination.page_size).all()
    return Page[CustomerOut](
        items=[CustomerOut.model_validate(c) for c in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/projects/{project_id}/customers",
    response_model=CustomerOut,
    status_code=201,
    summary="新增客户信息",
)
def create_customer_api(project_id: int, payload: CustomerCreate, db: Session = Depends(get_db)):
    try:
        return CustomerOut.model_validate(create_customer(db, project_id, payload.data))
    except SubmissionError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)


@router.get("/customers/{customer_id}", response_model=CustomerOut, summary="客户详情")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户信息不存在")
    return CustomerOut.model_validate(customer)


@router.put("/customers/{customer_id}", response_model=CustomerOut, summary="编辑客户信息")
def update_customer_api(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户信息不存在")
    try:
        return CustomerOut.model_validate(update_customer(db, customer, payload.data))
    except SubmissionError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)


@router.delete("/customers/{customer_id}", status_code=204, summary="删除客户信息")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户信息不存在")
    db.delete(customer)
    db.commit()
