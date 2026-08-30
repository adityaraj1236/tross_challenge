from app.linkedin.parser.blob_extractor import extract_json_blobs, merge_entity_graph


def test_extract_json_blobs_finds_embedded_code_tag(full_profile_html: str) -> None:
    blobs = extract_json_blobs(full_profile_html)
    assert len(blobs) == 1
    assert "included" in blobs[0]


def test_extract_json_blobs_returns_empty_for_page_without_blobs(minimal_profile_html: str) -> None:
    assert extract_json_blobs(minimal_profile_html) == []


def test_extract_json_blobs_ignores_malformed_json(malformed_profile_html: str) -> None:
    # Truncated JSON must not raise - it's simply skipped.
    assert extract_json_blobs(malformed_profile_html) == []


def test_merge_entity_graph_indexes_by_entity_urn(full_profile_html: str) -> None:
    blobs = extract_json_blobs(full_profile_html)
    graph = merge_entity_graph(blobs)
    assert "urn:li:fs_profile:ACoAA123" in graph
    assert graph["urn:li:fs_profile:ACoAA123"]["firstName"] == "Jane"


def test_merge_entity_graph_handles_no_included_key() -> None:
    assert merge_entity_graph([{"data": {}}]) == {}
