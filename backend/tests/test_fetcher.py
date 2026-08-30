from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInBlockedError,
    LinkedInChallengeError,
    LinkedInNotFoundError,
    LinkedInRateLimitError,
)
from app.linkedin.fetcher import LinkedInFetcher


def _make_fetcher(**overrides) -> LinkedInFetcher:
    defaults = {"max_retries": 1, "retry_backoff_seconds": 0}
    defaults.update(overrides)
    return LinkedInFetcher(Settings(**defaults))


def _response(status_code: int, url: str = "https://www.linkedin.com/in/jane-doe/", text: str = "<html></html>") -> httpx.Response:
    return httpx.Response(status_code=status_code, text=text, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_fetch_html_returns_body_on_success() -> None:
    fetcher = _make_fetcher()
    fetcher._client.get = AsyncMock(return_value=_response(200, text="<html>ok</html>"))
    body = await fetcher.fetch_html("https://www.linkedin.com/in/jane-doe/")
    assert body == "<html>ok</html>"


@pytest.mark.asyncio
async def test_fetch_html_raises_not_found_on_404() -> None:
    fetcher = _make_fetcher()
    fetcher._client.get = AsyncMock(return_value=_response(404))
    with pytest.raises(LinkedInNotFoundError):
        await fetcher.fetch_html("https://www.linkedin.com/in/does-not-exist/")


@pytest.mark.asyncio
async def test_fetch_html_raises_auth_error_on_403() -> None:
    fetcher = _make_fetcher()
    fetcher._client.get = AsyncMock(return_value=_response(403))
    with pytest.raises(LinkedInAuthError):
        await fetcher.fetch_html("https://www.linkedin.com/in/jane-doe/")


@pytest.mark.asyncio
async def test_fetch_html_raises_auth_error_on_authwall_redirect() -> None:
    fetcher = _make_fetcher()
    fetcher._client.get = AsyncMock(
        return_value=_response(200, url="https://www.linkedin.com/authwall?trk=x")
    )
    with pytest.raises(LinkedInAuthError):
        await fetcher.fetch_html("https://www.linkedin.com/in/jane-doe/")


@pytest.mark.asyncio
async def test_fetch_html_raises_challenge_error_on_security_checkpoint() -> None:
    fetcher = _make_fetcher()
    fetcher._client.get = AsyncMock(
        return_value=_response(200, text="<title>Security Verification</title>")
    )
    with pytest.raises(LinkedInChallengeError):
        await fetcher.fetch_html("https://www.linkedin.com/in/jane-doe/")


@pytest.mark.asyncio
async def test_fetch_html_raises_rate_limit_error_on_429() -> None:
    fetcher = _make_fetcher()
    fetcher._client.get = AsyncMock(return_value=_response(429))
    with pytest.raises(LinkedInRateLimitError):
        await fetcher.fetch_html("https://www.linkedin.com/in/jane-doe/")


@pytest.mark.asyncio
async def test_fetch_html_raises_blocked_error_on_redirect_loop_without_retrying() -> None:
    fetcher = _make_fetcher(max_retries=3)
    request = httpx.Request("GET", "https://www.linkedin.com/in/jane-doe/details/experience/")
    fetcher._client.get = AsyncMock(side_effect=httpx.TooManyRedirects("loop", request=request))

    with pytest.raises(LinkedInBlockedError):
        await fetcher.fetch_html("https://www.linkedin.com/in/jane-doe/details/experience/")

    # Deterministic failure - must not be retried max_retries times.
    assert fetcher._client.get.await_count == 1


def test_is_authenticated_reflects_configured_cookie() -> None:
    assert _make_fetcher(linkedin_li_at=None).is_authenticated is False
    assert _make_fetcher(linkedin_li_at="fake-cookie-value").is_authenticated is True


def test_csrf_header_derived_from_jsessionid() -> None:
    fetcher = _make_fetcher(linkedin_jsessionid="abc123")
    assert fetcher._client.headers["csrf-token"] == "abc123"
