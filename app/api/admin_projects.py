"""后台 - 项目动态 CRUD。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.models import Project, User
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(
    prefix="/api/admin/projects",
    tags=["项目管理"],
    dependencies=[Depends(get_current_user)],
)


def _to_out(project: Project) -> ProjectOut:
    return ProjectOut.model_validate(project)


@router.get("", response_model=Page[ProjectOut], summary="项目列表（分页/关键字）")
def list_projects(
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None, description="按名称搜索"),
    db: Session = Depends(get_db),
):
    stmt = select(Project)
    if q:
        stmt = stmt.where(or_(Project.name.like(f"%{q}%"), Project.slug.like(f"%{q}%")))
    total = len(db.scalars(stmt).all())
    items = (
        db.scalars(
            stmt.order_by(Project.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .all()
    )
    return Page[ProjectOut](
        items=[_to_out(p) for p in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=ProjectOut, status_code=201, summary="新建项目")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="slug 已被占用")
    db.refresh(project)
    return _to_out(project)


@router.get("/{project_id}", response_model=ProjectOut, summary="项目详情")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _to_out(project)


@router.put("/{project_id}", response_model=ProjectOut, summary="更新项目")
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="slug 已被占用")
    db.refresh(project)
    return _to_out(project)


@router.delete("/{project_id}", status_code=204, summary="删除项目（级联删除字段与客户数据）")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()
