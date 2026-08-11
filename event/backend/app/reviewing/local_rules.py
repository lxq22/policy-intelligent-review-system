import re

from .schemas import IssueDraft

AMBIGUOUS_TERMS = ("及时", "适当", "原则上")
REPEATED_PUNCTUATION = re.compile(r"([，。；：、！？])\1+")
ARTICLE_NUMBER = re.compile(r"第([零〇一二三四五六七八九十百两\d]+)条")


def review_locally(dimension: str, snapshots: list[dict]) -> list[IssueDraft]:
    if dimension == "semantic":
        return _semantic_rules(snapshots)
    if dimension == "rule":
        return _rule_rules(snapshots)
    return []


def _semantic_rules(snapshots: list[dict]) -> list[IssueDraft]:
    issues: list[IssueDraft] = []
    for clause in snapshots:
        text = clause.get("text", "")
        for term in AMBIGUOUS_TERMS:
            if term not in text:
                continue
            issues.append(
                IssueDraft(
                    source_clause_id=clause["clause_id"],
                    explanation=f'“{term}”缺少可直接执行的时间、条件或判断标准。',
                    consequence="不同执行人员可能采用不同标准，导致制度执行不一致。",
                    suggestion=f'将“{term}”改为明确的期限、适用条件或量化标准。',
                    details={"ambiguous_expression": term},
                )
            )
    return issues


def _rule_rules(snapshots: list[dict]) -> list[IssueDraft]:
    issues: list[IssueDraft] = []
    previous_number: int | None = None
    for clause in snapshots:
        clause_id = clause["clause_id"]
        original_no = clause.get("original_no", "")
        text = clause.get("text", "")
        number = _article_number(original_no)
        if number is None:
            issues.append(
                IssueDraft(
                    source_clause_id=clause_id,
                    explanation="条款未使用可识别的“第X条”编号结构。",
                    consequence="可能造成条款定位、引用和后续修订困难。",
                    suggestion="按“第X条”格式统一条款编号。",
                    details={"rule_category": "文本结构"},
                )
            )
        elif previous_number is not None and number != previous_number + 1:
            issues.append(
                IssueDraft(
                    source_clause_id=clause_id,
                    explanation=f"条款编号由第{previous_number}条跳至第{number}条，编号不连续。",
                    consequence="可能导致条款遗漏、重复或引用错误。",
                    suggestion="核对前后条款，并按连续顺序重新编号。",
                    details={"rule_category": "条款编号"},
                )
            )
        if number is not None:
            previous_number = number

        match = REPEATED_PUNCTUATION.search(text)
        if match:
            issues.append(
                IssueDraft(
                    source_clause_id=clause_id,
                    explanation=f'存在重复标点“{match.group(0)}”。',
                    consequence="影响制度文本的规范性和可读性。",
                    suggestion=f'将“{match.group(0)}”修改为单个“{match.group(1)}”。',
                    details={"rule_category": "行文规范"},
                )
            )
    return issues


def _article_number(value: str) -> int | None:
    match = ARTICLE_NUMBER.search(value)
    if not match:
        return None
    raw = match.group(1)
    if raw.isdigit():
        return int(raw)
    return _chinese_number(raw)


def _chinese_number(value: str) -> int | None:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if value in digits:
        return digits[value]
    total = 0
    current = 0
    for char in value:
        if char in digits:
            current = digits[char]
        elif char == "十":
            total += (current or 1) * 10
            current = 0
        elif char == "百":
            total += (current or 1) * 100
            current = 0
        else:
            return None
    return total + current
