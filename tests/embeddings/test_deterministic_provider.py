from cortex.embeddings.deterministic import DeterministicEmbeddingProvider


def test_deterministic_embedding_repeatability_and_version_changes() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8, version="emb-v1")
    same = provider.embed("sha256:text")
    repeated = provider.embed("sha256:text")
    changed_input = provider.embed("sha256:other")
    changed_version = DeterministicEmbeddingProvider(
        dimensions=8, version="emb-v2"
    ).embed("sha256:text")

    assert same == repeated
    assert len(same.vector) == 8
    assert same.vector_hash != changed_input.vector_hash
    assert same.vector_hash != changed_version.vector_hash
