import json

DIMENSION_RULES = {
    "semantic": "检查语义歧义、职责主体不清、条件或期限不明确。明确关注及时、适当、原则上等模糊表达。",
    "rule": "只检查文本结构、条款编号和行文规范；不要检查版式、字体、表格、扫描件或 OCR。待审条款可能是用户选择的非连续子集，不得仅因输入中的条款编号不连续就判断缺号。",
    "conflict": "只在给定候选对比条款中检查条款编号引用错误、不存在的引用、引用失效制度及前后规定冲突。",
    "consistency": "检查同一制度中的术语、责任主体、数值、期限和制度信息是否前后一致。",
}


def build_messages(
    dimension: str,
    source_snapshots: list[dict],
    candidate_snapshots: list[dict],
    local_findings: list[dict],
) -> list[dict[str, str]]:
    system = f"""你是当前项目单位的制度审查专家。当前维度：{dimension}。
{DIMENSION_RULES[dimension]}
只能依据输入条款判断，不得编造制度、条款、位置或证据。没有充分证据但值得提示时，将 insufficient_evidence 设为 true。
不要输出风险等级、置信度、页码。不要重复本地规则已经发现的相同问题。
只返回 JSON 对象，格式为：
{{"issues":[{{"source_clause_id":整数,"explanation":"判断说明","consequence":"可能后果","suggestion":"修改建议","insufficient_evidence":布尔值,"evidence_clause_ids":[整数],"details":{{}}}}]}}
source_clause_id 必须来自待审条款。冲突维度的 evidence_clause_ids 必须来自候选对比条款；一致性维度可引用其他待审条款。其他维度通常留空。
details 按维度填写：semantic 使用 ambiguous_expression；rule 使用 rule_category；conflict 使用 conflict_type；consistency 使用 consistency_type。"""
    data = {
        "source_clauses": source_snapshots,
        "candidate_clauses": candidate_snapshots if dimension == "conflict" else [],
        "local_findings": local_findings,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
    ]
