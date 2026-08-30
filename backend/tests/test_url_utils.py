import pytest

from app.linkedin.exceptions import InvalidProfileUrlError
from app.linkedin.url_utils import parse_profile_url


@pytest.mark.parametrize(
    "raw_url,expected_id",
    [
        ("https://www.linkedin.com/in/jane-doe/", "jane-doe"),
        ("https://www.linkedin.com/in/jane-doe", "jane-doe"),
        ("http://linkedin.com/in/jane-doe-12a34b567/", "jane-doe-12a34b567"),
        ("linkedin.com/in/jane-doe", "jane-doe"),
        ("https://www.linkedin.com/in/jane-doe/?extra=param", "jane-doe"),
        ("https://uk.linkedin.com/in/jane-doe/", "jane-doe"),
    ],
)
def test_parse_valid_profile_urls(raw_url: str, expected_id: str) -> None:
    ref = parse_profile_url(raw_url)
    assert ref.public_id == expected_id
    assert ref.canonical_url == f"https://www.linkedin.com/in/{expected_id}/"


@pytest.mark.parametrize(
    "raw_url",
    [
        "",
        "   ",
        "https://www.example.com/in/jane-doe/",
        "https://www.linkedin.com/company/example-corp/",
        "not a url at all",
        "https://www.linkedin.com/in//",
    ],
)
def test_parse_invalid_profile_urls_raises(raw_url: str) -> None:
    with pytest.raises(InvalidProfileUrlError):
        parse_profile_url(raw_url)
