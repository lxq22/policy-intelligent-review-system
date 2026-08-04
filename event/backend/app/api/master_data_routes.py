from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_reviewer, reviewer_permission
from ..database import get_db
from ..models import Category, Department, Unit, User
from ..schemas import NamedItemIn, NamedItemOut, UnitIn, UnitOut

router = APIRouter(prefix="/master-data", tags=["组织与分类"])


def unit_out(db: Session, unit: Unit) -> UnitOut:
    parent = db.get(Unit, unit.parent_id) if unit.parent_id else None
    return UnitOut(id=unit.id, name=unit.name, level=unit.level, parent_id=unit.parent_id, parent_name=parent.name if parent else None)


def validate_unit_parent(db: Session, payload: UnitIn, item_id: int | None = None) -> None:
    if payload.level == "一级单位":
        if payload.parent_id is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="一级单位不能设置所属一级单位")
        return
    if payload.parent_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="二级单位必须选择所属一级单位")
    if payload.parent_id == item_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="单位不能隶属于自身")
    parent = db.get(Unit, payload.parent_id)
    if not parent or parent.level != "一级单位":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="所属一级单位不存在或层级不正确")


@router.get("/departments", response_model=list[NamedItemOut])
def list_departments(_: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    return list(db.scalars(select(Department).order_by(Department.id)))


@router.post("/departments", response_model=NamedItemOut, status_code=201)
def create_department(payload: NamedItemIn, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = Department(name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/departments/{item_id}", response_model=NamedItemOut)
def update_department(item_id: int, payload: NamedItemIn, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = db.get(Department, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="部门不存在")
    item.name = payload.name
    db.commit()
    db.refresh(item)
    return item


@router.delete("/departments/{item_id}", status_code=204)
def delete_department(item_id: int, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = db.get(Department, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="部门不存在")
    db.delete(item)
    db.commit()


@router.get("/categories", response_model=list[NamedItemOut])
def list_categories(_: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    return list(db.scalars(select(Category).order_by(Category.id)))


@router.post("/categories", response_model=NamedItemOut, status_code=201)
def create_category(payload: NamedItemIn, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = Category(name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/categories/{item_id}", response_model=NamedItemOut)
def update_category(item_id: int, payload: NamedItemIn, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = db.get(Category, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="分类不存在")
    item.name = payload.name
    db.commit()
    db.refresh(item)
    return item


@router.delete("/categories/{item_id}", status_code=204)
def delete_category(item_id: int, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = db.get(Category, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="分类不存在")
    db.delete(item)
    db.commit()


@router.get("/units", response_model=list[UnitOut])
def list_units(_: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    return [unit_out(db, item) for item in db.scalars(select(Unit).order_by(Unit.id))]


@router.post("/units", response_model=UnitOut, status_code=201)
def create_unit(payload: UnitIn, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    validate_unit_parent(db, payload)
    item = Unit(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return unit_out(db, item)


@router.patch("/units/{item_id}", response_model=UnitOut)
def update_unit(item_id: int, payload: UnitIn, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = db.get(Unit, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="单位不存在")
    if item.level == "一级单位" and payload.level == "二级单位" and db.scalar(select(Unit.id).where(Unit.parent_id == item.id).limit(1)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该一级单位仍有所属二级单位，不能直接改为二级单位")
    validate_unit_parent(db, payload, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return unit_out(db, item)


@router.delete("/units/{item_id}", status_code=204)
def delete_unit(item_id: int, _: User = Depends(reviewer_permission("relation")), db: Session = Depends(get_db)):
    item = db.get(Unit, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="单位不存在")
    if db.scalar(select(Unit.id).where(Unit.parent_id == item.id).limit(1)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先调整或删除该一级单位下的二级单位")
    db.delete(item)
    db.commit()
