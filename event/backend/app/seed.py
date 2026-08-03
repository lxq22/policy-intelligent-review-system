from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    Category,
    Department,
    ManualRelation,
    OperationLog,
    Regulation,
    RegulationVersion,
    RelationSuggestion,
    ReviewRecord,
    Unit,
    User,
)


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)):
        return

    reviewer = User(username="reviewer", password_hash=hash_password("demo123"), name="李明", role="reviewer", enabled=True, department="制度审查室", perm_upload=True, perm_delete=True, perm_relation=True)
    limited = User(username="reviewer_limited", password_hash=hash_password("demo123"), name="周宁", role="reviewer", enabled=True, department="制度审查室")
    disabled = User(username="reviewer_disabled", password_hash=hash_password("demo123"), name="陈佳", role="reviewer", enabled=False, department="采购管理部", perm_upload=True, perm_relation=True)
    admin = User(username="admin", password_hash=hash_password("demo123"), name="系统管理员", role="admin", enabled=True, department="系统管理")
    db.add_all([reviewer, limited, disabled, admin])

    purchasing = Department(name="采购管理部")
    supply = Department(name="供应链管理部")
    finance = Department(name="财务部")
    hr = Department(name="人力资源部")
    categories = [Category(name=name) for name in ["采购管理", "合同管理", "供应商管理", "费用管理"]]
    headquarters = Unit(name="总部", level="一级单位")
    supply_center = Unit(name="供应链中心", level="一级单位")
    db.add_all([purchasing, supply, finance, hr, *categories, headquarters, supply_center])
    db.flush()
    procurement_unit = Unit(name="采购管理部", level="二级单位", parent_id=headquarters.id)
    finance_unit = Unit(name="财务部", level="二级单位", parent_id=headquarters.id)
    supplier_unit = Unit(name="供应链管理部", level="二级单位", parent_id=supply_center.id)
    db.add_all([procurement_unit, finance_unit, supplier_unit])
    db.flush()

    regulations = [
        Regulation(name="采购管理实施细则", code="CG-2026-03", department_id=purchasing.id, category_id=categories[0].id, unit_id=procurement_unit.id, hierarchy="二级单位制度", current_version="V2.1", publish_date=date(2026, 6, 18), effective_date=date(2026, 7, 1), status="生效中", scope="适用于本单位货物、服务和工程采购活动。", file_name="采购管理实施细则V2.1.docx", parse_status="解析成功"),
        Regulation(name="采购管理办法", code="CG-2025-01", department_id=purchasing.id, category_id=categories[0].id, unit_id=headquarters.id, hierarchy="一级单位制度", current_version="V3.0", publish_date=date(2025, 12, 20), effective_date=date(2026, 1, 1), status="生效中", scope="适用于一级单位及所属二级单位的采购管理。", file_name="采购管理办法V3.0.pdf", parse_status="解析成功"),
        Regulation(name="合同管理细则", code="HT-2026-02", department_id=purchasing.id, category_id=categories[1].id, unit_id=procurement_unit.id, hierarchy="二级单位制度", current_version="V1.2", effective_date=date(2026, 4, 1), status="生效中", scope="适用于本单位合同订立、履行及资料管理。", file_name="合同管理细则V1.2.docx", parse_status="解析成功"),
        Regulation(name="供应商管理规定", code="GY-2024-06", department_id=supply.id, category_id=categories[2].id, unit_id=supplier_unit.id, hierarchy="二级单位制度", current_version="V1.0", effective_date=date(2024, 7, 1), expiry_date=date(2026, 6, 30), status="已失效", scope="适用于供应商准入、评价和退出。", file_name="供应商管理规定V1.0.pdf", parse_status="解析成功"),
        Regulation(name="差旅费用管理办法", code="CW-2025-08", department_id=finance.id, category_id=categories[3].id, unit_id=headquarters.id, hierarchy="一级单位制度", current_version="V2.0", effective_date=date(2025, 9, 1), status="生效中", scope="适用于本单位工作人员公务出差费用管理。", file_name="差旅费用管理办法V2.0.docx", parse_status="解析失败"),
        Regulation(name="旧版采购审批细则", code="CG-2022-02", department_id=purchasing.id, category_id=categories[0].id, unit_id=procurement_unit.id, hierarchy="二级单位制度", current_version="V1.0", effective_date=date(2022, 3, 1), expiry_date=date(2025, 1, 31), status="已失效", scope="原适用于采购审批。", file_name="旧版采购审批细则.pdf", parse_status="解析成功", deleted_at=datetime(2026, 7, 25, 10, 8)),
    ]
    db.add_all(regulations)
    db.flush()

    for item in regulations:
        db.add(RegulationVersion(regulation_id=item.id, version=item.current_version, effective_date=item.effective_date, file_name=item.file_name, note="演示数据初始版本"))
    db.add(ManualRelation(source_id=regulations[0].id, target_id=regulations[3].id, relation_type="引用", source_kind="人工确认", note="正文疑似引用后确认", created_by=reviewer.id))
    db.add(RelationSuggestion(source_id=regulations[0].id, target_name="财务支出审批规定", relation_type="引用", evidence="正文中识别到疑似制度名称", status="待确认"))
    db.add(RelationSuggestion(source_id=regulations[0].id, target_id=regulations[4].id, target_name=regulations[4].name, relation_type="关联", evidence="正文涉及采购费用管理，提示人工确认其他相关制度", status="待确认"))
    db.add_all([
        OperationLog(operation_type="新增制度", regulation_id=regulations[0].id, regulation_name=regulations[0].name, operator_id=reviewer.id, operator_name=reviewer.name),
        OperationLog(operation_type="删除制度", regulation_id=regulations[5].id, regulation_name=regulations[5].name, operator_id=limited.id, operator_name=limited.name),
        ReviewRecord(record_code="采购管理实施细则-20260730-01", regulation_id=regulations[0].id, regulation_name=regulations[0].name),
        ReviewRecord(record_code="采购管理实施细则-20260721-02", regulation_id=regulations[0].id, regulation_name=regulations[0].name),
    ])
    db.commit()
