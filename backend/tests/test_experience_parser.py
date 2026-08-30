from bs4 import BeautifulSoup

from app.linkedin.parser.blob_extractor import extract_json_blobs, merge_entity_graph
from app.linkedin.parser.experience import parse_experience, parse_experience_from_html


def test_parse_experience_extracts_all_positions(full_profile_html: str) -> None:
    graph = merge_entity_graph(extract_json_blobs(full_profile_html))
    items = parse_experience(graph)
    assert len(items) == 2

    current = next(i for i in items if i["company"] == "Example Corp")
    assert current["title"] == "Senior Software Engineer"
    assert current["start_date"] == "Mar 2022"
    assert current["end_date"] is None
    assert current["duration"] == "Mar 2022 - Present"
    assert current["company_linkedin_url"] == "https://www.linkedin.com/company/example-corp/"
    assert current["company_logo_url"] == "https://media.licdn.com/dms/image/company/logo_200.png"

    past = next(i for i in items if i["company"] == "Prior Startup Inc")
    assert past["start_date"] == "Jun 2019"
    assert past["end_date"] == "Feb 2022"
    assert past["duration"] == "Jun 2019 - Feb 2022"


def test_parse_experience_returns_empty_list_when_no_positions(minimal_profile_html: str) -> None:
    graph = merge_entity_graph(extract_json_blobs(minimal_profile_html))
    assert parse_experience(graph) == []


def test_parse_experience_from_html_extracts_all_positions(mobile_full_soup: BeautifulSoup) -> None:
    items = parse_experience_from_html(mobile_full_soup)
    assert len(items) == 2

    current = next(i for i in items if i["company"] == "Example Corp")
    assert current["title"] == "Staff Engineer"
    assert current["start_date"] == "Mar 2022"
    assert current["end_date"] is None
    assert current["duration"] == "3 yrs 6 mos"
    assert current["location"] == "San Francisco, California"
    assert current["company_linkedin_url"] == "https://www.linkedin.com/company/example-corp"
    assert current["company_logo_url"].endswith("?logo1")
    assert "Leading the backend platform team" in current["description"]

    past = next(i for i in items if i["company"] == "Prior Startup Inc")
    assert past["title"] == "Software Engineer"
    assert past["start_date"] == "Jun 2019"
    assert past["end_date"] == "Feb 2022"
    assert past["duration"] == "2 yrs 9 mos"
    assert past["description"] is None


def test_parse_experience_from_html_returns_empty_list_when_section_absent(
    mobile_minimal_soup: BeautifulSoup,
) -> None:
    assert parse_experience_from_html(mobile_minimal_soup) == []
