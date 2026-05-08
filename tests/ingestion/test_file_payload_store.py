import pytest

from cortex.ingestion.payloads import FilePayloadStore, PayloadNotFoundError


def test_file_payload_store_round_trips_canonical_json(tmp_path) -> None:
    store = FilePayloadStore(tmp_path)

    first = store.put_json({"b": 2, "a": 1})
    second = store.put_json({"a": 1, "b": 2})

    assert first == second
    assert store.get(first.payload_ref) == b'{"a":1,"b":2}'


def test_file_payload_store_rejects_unknown_ref(tmp_path) -> None:
    store = FilePayloadStore(tmp_path)

    with pytest.raises(PayloadNotFoundError):
        store.get("memory://payloads/nope")
