"""后台 - 客户信息查询 / 新增 / 编辑 / 删除。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.core.validation import SubmissionError
from app.models import Customer
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import create_customer, get_project_or_404, update_customer

router = APIRouter(tags=["客户信息"], dependencies=[Depends(get_current_user)])


def _to_out(customer: Customer) -> CustomerOut:
    return CustomerOut.model_validate(customer)


@router.get(
    "/api/admin/projects/{project_id}/customers",
    response_model=Page[CustomerOut],
    summary="客户信息列表（分页 / 关键字）",
)
def list_customers(
    project_id: int,
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None, description="在提交的 JSON 全文中模糊搜索"),
    db: Session = Depends(get_db),
):
    get_project_or_404(db, project_id)
    stmt = db.query(Customer).filter(Customer.project_id == project_id)
    if q:
        # SQLite 中 JSON 以 TEXT 存储，直接对 data 列做 LIKE
        stmt = stmt.filter(text("data LIKE :pattern")).params(pattern=f"%{q}%")
    total = stmt.count()
    rows = (
        stmt.order_by(Customer.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    return Page[CustomerOut](
        items=[_to_out(c) for c in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/api/admin/projects/{project_id}/customers",
    response_model=CustomerOut,
    status_code=201,
    summary="后台手动新增客户信息",
)
def admin_create_customer(project_id: int, payload: CustomerCreate, db: Session = Depends(get_db)):
    try:
        return _to_out(create_customer(db, project_id, payload.data))
    except SubmissionError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)


@router.get("/api/admin/customers/{customer_id}", response_model=CustomerOut, summary="客户详情")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户信息不存在")
    return _to_out(customer)


@router.put("/api/admin/customers/{customer_id}", response_model=CustomerOut, summary="编辑客户信息")
def admin_update_customer(
    customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户信息不存在")
    try:
        return _to_out(update_customer(db, customer, payload.data))
    except SubmissionError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)


@router.delete("/api/admin/customers/{customer_id}", status_code=204, summary="删除客户信息")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户信息不存在")
    db.delete(customer)
    db.commit()
