from __future__ import annotations


class LinkedInError(Exception):
    """Base class for every error this service raises while talking to LinkedIn."""

    error_code = "UPSTREAM_ERROR"
    status_code = 502


class InvalidProfileUrlError(LinkedInError):
    """The supplied string is not a recognizable LinkedIn profile URL."""

    error_code = "INVALID_URL"
    status_code = 400


class LinkedInAuthError(LinkedInError):
    """LinkedIn rejected the request or redirected to a login/authwall page.

    Raised when the configured session cookie is missing, expired, or invalid.
    We never attempt to log in or bypass this - the caller must supply a
    fresh, authorized session via environment variables.
    """

    error_code = "AUTH_REQUIRED"
    status_code = 401


class LinkedInChallengeError(LinkedInError):
    """LinkedIn presented a security/CAPTCHA challenge.

    This is a deliberate stop condition: this service never attempts to
    solve or bypass CAPTCHAs or security checkpoints.
    """

    error_code = "CHALLENGE_REQUIRED"
    status_code = 403


class LinkedInNotFoundError(LinkedInError):
    """The profile does not exist, is not public, or the slug is wrong."""

    error_code = "PROFILE_NOT_FOUND"
    status_code = 404


class LinkedInRateLimitError(LinkedInError):
    """LinkedIn is throttling this client."""

    error_code = "RATE_LIMITED"
    status_code = 429


class LinkedInBlockedError(LinkedInError):
    """LinkedIn's anti-automation defenses rejected this request outright.

    Observed in practice as an infinite self-redirect (the same URL
    redirecting to itself) on routes LinkedIn treats as higher-risk for
    non-browser clients - most reliably on the `/details/<section>/`
    sub-pages, and on the main profile page too once a session/IP has sent
    enough requests in a short window to get soft-blocked. This is
    deterministic, so it is never retried - retrying just repeats the same
    loop and adds load against LinkedIn for no benefit.
    """

    error_code = "BLOCKED_BY_LINKEDIN"
    status_code = 403


class LinkedInParseError(LinkedInError):
    """The page was fetched successfully but no usable profile data was found.

    Usually means LinkedIn's markup/embedded-JSON shape has drifted since
    this parser was written.
    """

    error_code = "PARSE_ERROR"
    status_code = 502
