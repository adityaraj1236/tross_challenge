from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.linkedin.exceptions import LinkedInAuthError, LinkedInParseError
from app.linkedin.service import LinkedInProfileService


class _FakeFetcher:
    """Stands in for LinkedInFetcher so service tests never touch the network."""

    def __init__(self, html_by_url: dict[str, str] | None = None, error: Exception | None = None):
        self._html_by_url = html_by_url or {}
        self._error = error
        self.is_authenticated = True

    async def fetch_html(self, url: str) -> str:
        if self._error is not None:
            raise self._error
        return self._html_by_url.get(url, "<html><head><title>LinkedIn</title></head><body></body></html>")

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_get_profile_raises_when_main_page_fetch_fails() -> None:
    service = LinkedInProfileService(Settings(), fetcher=_FakeFetcher(error=LinkedInAuthError("no session")))
    with pytest.raises(LinkedInAuthError):
        await service.get_profile("https://www.linkedin.com/in/jane-doe/")


@pytest.mark.asyncio
async def test_get_profile_raises_parse_error_when_nothing_extractable() -> None:
    fetcher = _FakeFetcher(html_by_url={})  # every page resolves to the bare "LinkedIn" title stub
    service = LinkedInProfileService(Settings(), fetcher=fetcher)
    with pytest.raises(LinkedInParseError):
        await service.get_profile("https://www.linkedin.com/in/jane-doe/")


@pytest.mark.asyncio
async def test_get_profile_succeeds_with_full_fixture(full_profile_html: str) -> None:
    ref_url = "https://www.linkedin.com/in/jane-doe/"
    fetcher = _FakeFetcher(html_by_url={ref_url: full_profile_html})
    service = LinkedInProfileService(Settings(), fetcher=fetcher)

    response = await service.get_profile(ref_url)

    assert response.success is True
    assert response.data.name == "Jane Doe"
    assert len(response.data.experience) == 2
    assert len(response.data.education) == 1


@pytest.mark.asyncio
async def test_get_profile_falls_back_to_html_meta_when_no_data_graph(minimal_profile_html: str) -> None:
    ref_url = "https://www.linkedin.com/in/john-smith/"
    fetcher = _FakeFetcher(html_by_url={ref_url: minimal_profile_html})
    service = LinkedInProfileService(Settings(), fetcher=fetcher)

    response = await service.get_profile(ref_url)

    assert response.partial is True
    assert response.data.name == "John Smith"
    assert response.data.experience == []
    assert any("No experience data" in w for w in response.warnings)


@pytest.mark.asyncio
async def test_get_profile_succeeds_end_to_end_with_mobile_html(mobile_full_html: str) -> None:
    # The primary path in practice: no JSON graph, everything from the
    # mobile-rendered HTML - full sections, not just the top card.
    ref_url = "https://www.linkedin.com/in/jordan-example/"
    fetcher = _FakeFetcher(html_by_url={ref_url: mobile_full_html})
    service = LinkedInProfileService(Settings(), fetcher=fetcher)

    response = await service.get_profile(ref_url)

    assert response.success is True
    assert response.data.name == "Jordan Example"
    assert response.data.about is not None
    assert len(response.data.experience) == 2
    assert len(response.data.education) == 1
    assert len(response.data.skills) == 2
    assert len(response.data.certifications) == 1
    assert len(response.data.languages) == 2
    assert response.partial is False
    assert response.warnings == []
