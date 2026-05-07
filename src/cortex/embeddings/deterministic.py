from __future__ import annotations

from dataclasses import dataclass

from cortex.ingestion.payloads import sha256_digest


@dataclass(frozen=True)
class EmbeddingOutput:
    vector: list[float]
    vector_hash: str


class DeterministicEmbeddingProvider:
    def __init__(self, dimensions: int = 16, version: str = "deterministic-v1") -> None:
        self.dimensions = dimensions
        self.version = version

    def embed(self, input_text_hash: str) -> EmbeddingOutput:
        seed = sha256_digest(f"{self.version}:{input_text_hash}".encode()).removeprefix(
            "sha256:"
        )
        values = []
        for index in range(self.dimensions):
            start = (index * 4) % len(seed)
            number = int(seed[start : start + 4], 16)
            values.append(round((number / 65535.0) * 2 - 1, 6))
        vector_bytes = ",".join(str(value) for value in values).encode()
        return EmbeddingOutput(vector=values, vector_hash=sha256_digest(vector_bytes))
