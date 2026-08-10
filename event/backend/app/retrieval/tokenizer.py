import re

import jieba


def tokenize(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text)
    words = [item.strip() for item in jieba.lcut(normalized) if item.strip()]
    bigrams = [normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))]
    return words + bigrams
