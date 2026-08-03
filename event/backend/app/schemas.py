from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class PermissionSet(BaseModel):
    upload: bool = False
    delete: bool = False
    relation: bool = False


class UserOut(BaseModel):
    id: int
    username: str
    name: Optional[str] = None
    role: Literal["reviewer", "admin"]
    enabled: bool
    department: Optional[str] = None
    permissions: PermissionSet


class LoginIn(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    name: Optional[str] = None
    department: Optional[str] = None
    password: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    enabled: Optional[bool] = None


class PermissionUpdate(BaseModel):
    upload: bool
    delete: bool
    relation: bool


class NamedItemIn(BaseModel):
    name: Optional[str] = None


class NamedItemOut(BaseModel):
    id: int
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UnitIn(BaseModel):
    name: Optional[str] = None
    level: Literal["一级单位", "二级单位"] = "二级单位"
    parent_id: Optional[int] = None


class UnitOut(UnitIn):
    id: int
    parent_name: Optional[str] = None


class VersionIn(BaseModel):
    version: Optional[str] = None
    effective_date: Optional[date] = None
    file_name: Optional[str] = None
    note: Optional[str] = None


class VersionOut(VersionIn):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RelationOut(BaseModel):
    id: str
    type: str
    target_id: int
    target_name: str
    source: str
    note: Optional[str] = None


class RelationCreate(BaseModel):
    target_id: int
    type: Literal["上位", "下位", "关联", "引用", "被引用", "版本替代"]
    note: Optional[str] = None


class SuggestionOut(BaseModel):
    id: int
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    type: str
    evidence: Optional[str] = None
    status: str


class RegulationIn(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[int] = None
    category_id: Optional[int] = None
    unit_id: Optional[int] = None
    hierarchy: Optional[Literal["一级单位制度", "二级单位制度"]] = None
    version: Optional[str] = None
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[Literal["生效中", "已失效"]] = None
    scope: Optional[str] = None
    file_name: Optional[str] = None


class RegulationOut(BaseModel):
    id: int
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[int] = None
    department: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[str] = None
    unit_id: Optional[int] = None
    unit: Optional[str] = None
    hierarchy: Optional[str] = None
    version: Optional[str] = None
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    scope: Optional[str] = None
    file_name: Optional[str] = None
    parse_status: str
    deleted: bool
    created_at: datetime
    updated_at: datetime
    versions: list[VersionOut] = []
    relations: list[RelationOut] = []


class OperationLogOut(BaseModel):
    id: int
    type: str
    regulation_id: Optional[int] = None
    regulation_name: Optional[str] = None
    operator: Optional[str] = None
    operated_at: datetime
    report_count: int = 0


class ResetPasswordOut(BaseModel):
    temporary_password: str
