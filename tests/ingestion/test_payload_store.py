from cortex.ingestion.payloads import InMemoryPayloadStore, canonical_json_bytes


def test_canonical_json_hashing_is_deterministic() -> None:
    store = InMemoryPayloadStore()
    left = store.put_json({"b": [2, {"a": 1}], "a": "x"})
    right = store.put_json({"a": "x", "b": [2, {"a": 1}]})

    assert left == right
    assert store.write_count == 1
    assert store.get(left.payload_ref) == canonical_json_bytes(
        {"a": "x", "b": [2, {"a": 1}]}
    )


def test_payload_ref_points_to_hashed_bytes() -> None:
    store = InMemoryPayloadStore()
    stored = store.put_bytes(b"provider bytes")

    assert stored.payload_hash.startswith("sha256:")
    assert stored.payload_size_bytes == len(b"provider bytes")
    assert store.get(stored.payload_ref) == b"provider bytes"
