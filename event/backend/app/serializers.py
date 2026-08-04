from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import OperationLog, Regulation, ReviewRecord, Unit, User
from .schemas import OperationLogOut, PermissionSet, RegulationOut, UserOut, VersionOut
from .services.relations import collect_relations


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        name=user.name,
        role=user.role,
        enabled=user.enabled,
        department=user.department,
        permissions=PermissionSet(
            upload=user.perm_upload,
            delete=user.perm_delete,
            relation=user.perm_relation,
        ),
    )


def regulation_out(db: Session, regulation: Regulation, include_details: bool = False) -> RegulationOut:
    return RegulationOut(
        id=regulation.id,
        name=regulation.name,
        code=regulation.code,
        department_id=regulation.department_id,
        department=regulation.department.name if regulation.department else None,
        category_id=regulation.category_id,
        category=regulation.category.name if regulation.category else None,
        unit_id=regulation.unit_id,
        unit=regulation.unit.name if regulation.unit else None,
        hierarchy=regulation.hierarchy,
        version=regulation.current_version,
        publish_date=regulation.publish_date,
        effective_date=regulation.effective_date,
        expiry_date=regulation.expiry_date,
        status=regulation.status,
        scope=regulation.scope,
        file_name=regulation.file_name,
        parse_status=regulation.parse_status,
        deleted=regulation.deleted_at is not None,
        created_at=regulation.created_at,
        updated_at=regulation.updated_at,
        versions=[VersionOut.model_validate(item) for item in regulation.versions] if include_details else [],
        relations=collect_relations(db, regulation) if include_details else [],
    )


def operation_log_out(db: Session, log: OperationLog) -> OperationLogOut:
    report_count = db.scalar(
        select(func.count(ReviewRecord.id)).where(ReviewRecord.regulation_id == log.regulation_id)
    ) or 0
    return OperationLogOut(
        id=log.id,
        type=log.operation_type,
        regulation_id=log.regulation_id,
        regulation_name=log.regulation_name,
        operator=log.operator_name,
        operated_at=log.operated_at,
        report_count=report_count,
    )
