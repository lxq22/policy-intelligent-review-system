from __future__ import annotations

import hashlib
import math
from typing import Protocol

from .tokenizer import tokenize


class EmbeddingProvider(Protocol):
    model_name: str

    def embed(self, text: str) -> list[float]: ...


class DeterministicEmbeddingProvider:
    model_name = "local-hash-zh-v1"
    dimensions = 256

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[digest[0]] += 1.0 if digest[1] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
