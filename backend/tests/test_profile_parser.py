from bs4 import BeautifulSoup

from app.linkedin.parser.blob_extractor import extract_json_blobs, merge_entity_graph
from app.linkedin.parser.profile import parse_basic_profile, parse_basic_profile_from_html


def _graph(html: str):
    return merge_entity_graph(extract_json_blobs(html))


def test_parse_basic_profile_extracts_core_fields(full_profile_html: str) -> None:
    result = parse_basic_profile(_graph(full_profile_html))
    assert result["name"] == "Jane Doe"
    assert result["headline"] == "Senior Software Engineer at Example Corp"
    assert result["location"] == "San Francisco Bay Area"
    assert "distributed systems" in result["about"]
    assert result["open_to_work"] is False
    assert result["follower_count"] == 4820


def test_parse_basic_profile_resolves_largest_image_artifact(full_profile_html: str) -> None:
    result = parse_basic_profile(_graph(full_profile_html))
    assert result["profile_image_url"] == "https://media.licdn.com/dms/image/profile/400_400.jpg"


def test_parse_basic_profile_returns_empty_dict_when_no_profile_entity(minimal_profile_html: str) -> None:
    assert parse_basic_profile(_graph(minimal_profile_html)) == {}


def test_parse_basic_profile_from_html_meta_fallback(minimal_profile_html: str) -> None:
    # No mobile top-card markup at all here - must fall back to <title>/meta tags.
    soup = BeautifulSoup(minimal_profile_html, "lxml")
    result = parse_basic_profile_from_html(soup)
    assert result["name"] == "John Smith"
    assert "Product Manager" in result["headline"]
    assert result["profile_image_url"] == "https://media.example.com/john-smith.jpg"


def test_parse_basic_profile_from_html_ignores_bare_linkedin_title() -> None:
    soup = BeautifulSoup("<html><head><title>LinkedIn</title></head></html>", "lxml")
    result = parse_basic_profile_from_html(soup)
    assert "name" not in result


def test_parse_basic_profile_from_html_extracts_mobile_top_card(mobile_full_soup: BeautifulSoup) -> None:
    result = parse_basic_profile_from_html(mobile_full_soup)
    assert result["name"] == "Jordan Example"
    assert result["headline"] == "Staff Engineer at Example Corp | Building developer tools"
    assert result["location"] == "San Francisco Bay Area"
    assert result["follower_count"] == 4820
    assert "distributed systems" in result["about"]


def test_parse_basic_profile_from_html_extracts_images_via_delayed_url(mobile_full_soup: BeautifulSoup) -> None:
    result = parse_basic_profile_from_html(mobile_full_soup)
    assert result["profile_image_url"].endswith("t=photo")
    assert result["cover_image_url"].endswith("t=cover")


def test_parse_basic_profile_from_html_minimal_top_card_only(mobile_minimal_soup: BeautifulSoup) -> None:
    result = parse_basic_profile_from_html(mobile_minimal_soup)
    assert result["name"] == "Taylor Minimal"
    assert result["headline"] == "Product Manager"
    assert result["location"] == "Austin, Texas, United States"
    assert "profile_image_url" not in result
