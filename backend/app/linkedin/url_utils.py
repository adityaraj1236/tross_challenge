from __future__ import annotations

import re
from dataclasses import dataclass

from .exceptions import InvalidProfileUrlError

_PROFILE_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.|[a-z]{2,3}\.)?linkedin\.com/in/([^/?#]+)/?",
    re.IGNORECASE,
)

# LinkedIn public-profile identifiers are alphanumeric + hyphen, optionally
# suffixed with a locale/dedup token e.g. "jane-doe-12a34b567".
_PUBLIC_ID_RE = re.compile(r"^[a-zA-Z0-9\-]{3,100}$")


@dataclass(frozen=True)
class ProfileRef:
    public_id: str
    canonical_url: str


def parse_profile_url(raw_url: str) -> ProfileRef:
    """Validate and normalize a LinkedIn profile URL into a ProfileRef.

    Raises InvalidProfileUrlError on anything that isn't a linkedin.com/in/<id> URL.
    """
    if not raw_url or not raw_url.strip():
        raise InvalidProfileUrlError("LinkedIn profile URL is required.")

    match = _PROFILE_URL_RE.search(raw_url.strip())
    if not match:
        raise InvalidProfileUrlError(
            "URL does not look like a LinkedIn profile URL "
            "(expected something like https://www.linkedin.com/in/<public-id>/)."
        )

    public_id = match.group(1).strip("/")
    if not public_id or not _PUBLIC_ID_RE.match(public_id):
        raise InvalidProfileUrlError("Could not extract a valid profile identifier from the URL.")

    return ProfileRef(
        public_id=public_id,
        canonical_url=f"https://www.linkedin.com/in/{public_id}/",
    )
