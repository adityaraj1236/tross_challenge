from __future__ import annotations

import asyncio
import random
from typing import Optional

import httpx

from ..config import Settings
from ..logging_config import get_logger, log_with_context
from .exceptions import (
    LinkedInAuthError,
    LinkedInBlockedError,
    LinkedInChallengeError,
    LinkedInError,
    LinkedInNotFoundError,
    LinkedInRateLimitError,
)

logger = get_logger(__name__)

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

# LinkedIn responds to the SAME /in/<slug>/ URL very differently depending on
# whether the request looks like it came from a mobile browser. A desktop UA
# gets a client-heavy React shell (~1MB) where Experience/Education/Skills/
# About are all loaded by a follow-up JS fetch this service cannot trigger. A
# mobile UA - with matching `sec-ch-ua-mobile`/`sec-ch-ua-platform` client
# hints - gets a much smaller (~180KB), fully server-rendered page where all
# of those sections are already in the initial HTML, confirmed against a live
# authenticated fetch (see README section 5). This is the entire reason the
# parsers in this package target that markup shape.
_MOBILE_CLIENT_HINT_HEADERS = {
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
}

_CHALLENGE_PATH_MARKERS = ("/checkpoint/", "/authwall", "/uas/login")
_CHALLENGE_TITLE_MARKERS = (
    "security verification",
    "let's do a quick security check",
    "verify you're a human",
)


class LinkedInFetcher:
    """Direct-HTTP client for LinkedIn profile pages. No browser involved.

    Authentication is purely cookie-based: the caller supplies an `li_at`
    (and optionally `JSESSIONID`) session cookie via environment variables.
    This class never logs in, never solves challenges, and never fabricates
    a session - if LinkedIn responds with an authwall or checkpoint, that is
    surfaced as a typed error instead of being worked around.
    """

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self._settings = settings
        cookies = self._build_cookies(settings)
        headers = self._build_headers(settings, cookies)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            cookies=cookies,
            headers=headers,
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            # LinkedIn's bot defenses reject some routes with an infinite
            # self-redirect. A low cap makes that fail fast (one wasted round
            # trip instead of the default 20) instead of hammering LinkedIn.
            max_redirects=5,
        )

    @staticmethod
    def _build_cookies(settings: Settings) -> dict[str, str]:
        cookies: dict[str, str] = {}
        if settings.linkedin_li_at:
            cookies["li_at"] = settings.linkedin_li_at
        if settings.linkedin_jsessionid:
            jsessionid = settings.linkedin_jsessionid.strip('"')
            cookies["JSESSIONID"] = f'"{jsessionid}"'
        if settings.linkedin_extra_cookies:
            for part in settings.linkedin_extra_cookies.split(";"):
                if "=" in part:
                    key, _, value = part.strip().partition("=")
                    key = key.strip()
                    if key:
                        cookies[key] = value.strip()
        return cookies

    @staticmethod
    def _build_headers(settings: Settings, cookies: dict[str, str]) -> dict[str, str]:
        headers = {
            "User-Agent": settings.linkedin_user_agent or _DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            **_MOBILE_CLIENT_HINT_HEADERS,
        }
        if "JSESSIONID" in cookies:
            # LinkedIn expects the CSRF token to equal the (unquoted) JSESSIONID value.
            headers["csrf-token"] = cookies["JSESSIONID"].strip('"')
        return headers

    @property
    def is_authenticated(self) -> bool:
        return bool(self._settings.linkedin_li_at)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_html(self, url: str) -> str:
        """GET a LinkedIn page and return its raw HTML, with retries and
        response classification. Raises a typed LinkedInError subclass on
        anything that isn't a clean 2xx profile page.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self._settings.max_retries + 1):
            try:
                response = await self._client.get(url)
                return self._classify_and_return(response, url)
            except LinkedInError:
                raise
            except httpx.TooManyRedirects as exc:
                # Deterministic: LinkedIn is redirecting this request to itself
                # (or in a loop). Retrying replays the exact same loop, so we
                # fail immediately instead of repeating it max_retries times.
                log_with_context(
                    logger, "WARNING", "LinkedIn redirected this request in a loop - treating as blocked",
                    context={"url": url},
                )
                raise LinkedInBlockedError(
                    "LinkedIn redirected this request to itself repeatedly, which is how its "
                    "automated-traffic defenses reject requests on this route. This is not "
                    "bypassed - if it persists, this session/IP is likely being throttled; "
                    "wait before retrying."
                ) from exc
            except httpx.TimeoutException as exc:
                last_error = exc
            except httpx.HTTPError as exc:
                last_error = exc

            if attempt < self._settings.max_retries:
                delay = self._settings.retry_backoff_seconds * attempt + random.uniform(0, 0.5)
                log_with_context(
                    logger, "WARNING",
                    "LinkedIn fetch failed, retrying",
                    context={"url": url, "attempt": attempt, "error": str(last_error)},
                )
                await asyncio.sleep(delay)

        log_with_context(
            logger, "ERROR",
            "LinkedIn fetch failed after all retries",
            context={"url": url, "max_retries": self._settings.max_retries, "error": str(last_error)},
        )
        raise LinkedInError(f"Failed to reach LinkedIn after {self._settings.max_retries} attempts: {last_error}")

    def _classify_and_return(self, response: httpx.Response, requested_url: str) -> str:
        status = response.status_code
        final_url = str(response.url)

        if status == 404:
            raise LinkedInNotFoundError(f"Profile not found: {requested_url}")
        if status in (429, 999):
            raise LinkedInRateLimitError("LinkedIn is rate-limiting this client.")
        if status in (401, 403):
            raise LinkedInAuthError(
                "LinkedIn rejected the request. The session cookie may be missing, expired, or invalid."
            )
        if status >= 500:
            raise LinkedInError(f"LinkedIn returned a server error ({status}).")

        if any(marker in final_url for marker in _CHALLENGE_PATH_MARKERS):
            raise LinkedInAuthError(
                "LinkedIn redirected to a login/authwall/checkpoint page. "
                "A valid, non-expired li_at session cookie is required for this profile."
            )

        body = response.text
        lowered_head = body[:6000].lower()
        if any(marker in lowered_head for marker in _CHALLENGE_TITLE_MARKERS):
            raise LinkedInChallengeError(
                "LinkedIn presented a security verification challenge for this request. "
                "This service does not attempt to bypass it - retry later with a fresh authorized session."
            )

        return body
