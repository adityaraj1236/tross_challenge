from bs4 import BeautifulSoup

from app.linkedin.parser.blob_extractor import extract_json_blobs, merge_entity_graph
from app.linkedin.parser.education import parse_education, parse_education_from_html


def test_parse_education_extracts_entry(full_profile_html: str) -> None:
    graph = merge_entity_graph(extract_json_blobs(full_profile_html))
    items = parse_education(graph)
    assert len(items) == 1

    entry = items[0]
    assert entry["institution"] == "State University"
    assert entry["degree"] == "B.S."
    assert entry["field_of_study"] == "Computer Science"
    assert entry["start_date"] == "2015"
    assert entry["end_date"] == "2019"
    assert entry["institution_linkedin_url"] == "https://www.linkedin.com/school/state-university/"
    assert entry["institution_logo_url"] == "https://media.licdn.com/dms/image/school/logo_100.png"


def test_parse_education_returns_empty_list_when_no_entries(minimal_profile_html: str) -> None:
    graph = merge_entity_graph(extract_json_blobs(minimal_profile_html))
    assert parse_education(graph) == []


def test_parse_education_from_html_extracts_entry(mobile_full_soup: BeautifulSoup) -> None:
    items = parse_education_from_html(mobile_full_soup)
    assert len(items) == 1

    entry = items[0]
    assert entry["institution"] == "State University"
    assert entry["degree"] == "B.S."
    assert entry["field_of_study"] == "Computer Science"
    assert entry["start_date"] == "2015"
    assert entry["end_date"] == "2019"
    assert entry["institution_linkedin_url"] == "https://www.linkedin.com/school/state-university/"
    assert entry["institution_logo_url"].endswith("?logo3")


def test_parse_education_from_html_returns_empty_list_when_section_absent(
    mobile_minimal_soup: BeautifulSoup,
) -> None:
    assert parse_education_from_html(mobile_minimal_soup) == []
