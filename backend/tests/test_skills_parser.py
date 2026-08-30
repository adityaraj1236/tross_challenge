from bs4 import BeautifulSoup

from app.linkedin.parser.blob_extractor import extract_json_blobs, merge_entity_graph
from app.linkedin.parser.certifications import parse_certifications, parse_certifications_from_html
from app.linkedin.parser.languages import parse_languages, parse_languages_from_html
from app.linkedin.parser.skills import parse_skills, parse_skills_from_html


def _graph(html: str):
    return merge_entity_graph(extract_json_blobs(html))


def test_parse_skills_extracts_names_and_endorsements(full_profile_html: str) -> None:
    items = parse_skills(_graph(full_profile_html))
    names = {i["name"] for i in items}
    assert names == {"Python", "Distributed Systems"}
    python = next(i for i in items if i["name"] == "Python")
    assert python["endorsement_count"] == 42


def test_parse_skills_empty_for_minimal_profile(minimal_profile_html: str) -> None:
    assert parse_skills(_graph(minimal_profile_html)) == []


def test_parse_certifications(full_profile_html: str) -> None:
    items = parse_certifications(_graph(full_profile_html))
    assert len(items) == 1
    cert = items[0]
    assert cert["name"] == "AWS Certified Solutions Architect"
    assert cert["issuing_organization"] == "Amazon Web Services"
    assert cert["issue_date"] == "May 2021"
    assert cert["credential_id"] == "ABC123XYZ"


def test_parse_languages(full_profile_html: str) -> None:
    items = parse_languages(_graph(full_profile_html))
    assert len(items) == 2
    english = next(i for i in items if i["name"] == "English")
    assert english["proficiency"] == "Native or bilingual proficiency"


def test_parse_skills_from_html_dedupes_and_extracts_names(mobile_full_soup: BeautifulSoup) -> None:
    items = parse_skills_from_html(mobile_full_soup)
    names = [i["name"] for i in items]
    assert names == ["Python", "Distributed Systems"]  # fixture lists "Python" twice
    assert all(i["endorsement_count"] is None for i in items)


def test_parse_skills_from_html_empty_when_section_absent(mobile_minimal_soup: BeautifulSoup) -> None:
    assert parse_skills_from_html(mobile_minimal_soup) == []


def test_parse_certifications_from_html(mobile_full_soup: BeautifulSoup) -> None:
    items = parse_certifications_from_html(mobile_full_soup)
    assert len(items) == 1
    cert = items[0]
    assert cert["name"] == "AWS Certified Solutions Architect"
    assert cert["issuing_organization"] == "Amazon Web Services"


def test_parse_certifications_from_html_empty_when_section_absent(mobile_minimal_soup: BeautifulSoup) -> None:
    assert parse_certifications_from_html(mobile_minimal_soup) == []


def test_parse_languages_from_html(mobile_full_soup: BeautifulSoup) -> None:
    items = parse_languages_from_html(mobile_full_soup)
    names = {i["name"] for i in items}
    assert names == {"English", "Spanish"}
    assert all(i["proficiency"] is None for i in items)


def test_parse_languages_from_html_empty_when_section_absent(mobile_minimal_soup: BeautifulSoup) -> None:
    assert parse_languages_from_html(mobile_minimal_soup) == []
