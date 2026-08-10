from datetime import UTC, date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="reviewer")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    department: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    perm_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    perm_delete: Mapped[bool] = mapped_column(Boolean, default=False)
    perm_relation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    sessions: Mapped[list["LoginSession"]] = relationship(cascade="all, delete-orphan")


class LoginSession(Base):
    __tablename__ = "login_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    level: Mapped[str] = mapped_column(String(20), default="二级单位")
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), nullable=True)


class Regulation(Base):
    __tablename__ = "regulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    hierarchy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    publish_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="待解析")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    department: Mapped[Optional[Department]] = relationship()
    category: Mapped[Optional[Category]] = relationship()
    unit: Mapped[Optional[Unit]] = relationship(foreign_keys=[unit_id])
    versions: Mapped[list["RegulationVersion"]] = relationship(cascade="all, delete-orphan", order_by="desc(RegulationVersion.id)")


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"
    __table_args__ = (
        CheckConstraint(
            "parse_status IN ('待解析', '解析中', '解析成功', '解析失败')",
            name="ck_regulation_version_parse_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regulation_id: Mapped[int] = mapped_column(ForeignKey("regulations.id", ondelete="CASCADE"), index=True)
    version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stored_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="待解析")
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    clauses: Mapped[list["Clause"]] = relationship(cascade="all, delete-orphan")


class TemporaryReviewFile(Base):
    __tablename__ = "temporary_review_files"
    __table_args__ = (
        CheckConstraint(
            "parse_status IN ('待解析', '解析中', '解析成功', '解析失败')",
            name="ck_temporary_file_parse_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    parse_status: Mapped[str] = mapped_column(String(20), default="待解析")
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    clauses: Mapped[list["Clause"]] = relationship(cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"
    __table_args__ = (
        CheckConstraint(
            "(regulation_version_id IS NOT NULL AND temporary_file_id IS NULL) OR "
            "(regulation_version_id IS NULL AND temporary_file_id IS NOT NULL)",
            name="ck_clause_exactly_one_source",
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regulation_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("regulation_versions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    temporary_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("temporary_review_files.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    original_no: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(30), default="article")
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    paragraph_start: Mapped[int] = mapped_column(Integer)
    paragraph_end: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(256).with_variant(JSON(), "sqlite")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ManualRelation(Base):
    __tablename__ = "manual_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("regulations.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("regulations.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(30))
    source_kind: Mapped[str] = mapped_column(String(30), default="手工添加")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RelationSuggestion(Base):
    __tablename__ = "relation_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("regulations.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[Optional[int]] = mapped_column(ForeignKey("regulations.id", ondelete="SET NULL"), nullable=True)
    target_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relation_type: Mapped[str] = mapped_column(String(30), default="引用")
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="待确认")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(30))
    regulation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    regulation_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    operator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_code: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    regulation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    temporary_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("temporary_review_files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    regulation_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default="regulation")
    dimensions: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_snapshot: Mapped[list[dict]] = mapped_column(JSON, default=list)
    candidate_snapshot: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
