from collections import defaultdict


def rrf(
    keyword_ids: list[int], vector_ids: list[int], k: int = 60
) -> list[tuple[int, float, list[str]]]:
    scores: dict[int, float] = defaultdict(float)
    evidence: dict[int, list[str]] = defaultdict(list)
    for label, values in (("关键词", keyword_ids), ("向量", vector_ids)):
        for rank, item_id in enumerate(values, start=1):
            scores[item_id] += 1.0 / (k + rank)
            evidence[item_id].append(label)
    return sorted(
        ((item_id, score, evidence[item_id]) for item_id, score in scores.items()),
        key=lambda item: (-item[1], item[0]),
    )
