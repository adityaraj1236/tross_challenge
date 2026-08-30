from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from .dom_utils import clean_text, direct_text
from .entity_graph import EntityGraph, first_present, type_name
from .images import extract_vector_image_url

_PROFILE_TYPE_SUFFIXES = (
    "identity.profile.Profile",
)


def find_profile_entity(graph: EntityGraph) -> Optional[dict[str, Any]]:
    """Locate the primary Profile entity in the entity graph.

    Kept as a defensive first attempt (see `parser/blob_extractor.py`) in
    case LinkedIn resumes embedding a normalized JSON data graph in profile
    HTML - as of this writing it does not, so `parse_basic_profile_from_html`
    below is the mechanism this implementation actually relies on.
    """
    candidates = [e for e in graph.values() if type_name(e).endswith(_PROFILE_TYPE_SUFFIXES)]
    if not candidates:
        return None
    candidates.sort(key=lambda e: bool(first_present(e, "headline", "summary")), reverse=True)
    return candidates[0]


def parse_basic_profile(graph: EntityGraph) -> dict[str, Any]:
    """Extract name/headline/location/about/images/open_to_work from the graph.

    Returns an empty dict (never raises) if no Profile entity was found -
    the caller falls back to `parse_basic_profile_from_html` in that case.
    """
    entity = find_profile_entity(graph)
    if not entity:
        return {}

    first_name = entity.get("firstName") or ""
    last_name = entity.get("lastName") or ""
    name = f"{first_name} {last_name}".strip() or None

    location = first_present(entity, "geoLocationName", "locationName", "location")

    profile_image_url = extract_vector_image_url(
        entity.get("profilePicture") or entity.get("displayPictureUrl")
    )
    cover_image_url = extract_vector_image_url(
        entity.get("backgroundImage") or entity.get("backgroundCoverImage")
    )

    return {
        "name": name,
        "headline": first_present(entity, "headline"),
        "location": location,
        "about": first_present(entity, "summary", "about"),
        "profile_image_url": profile_image_url,
        "cover_image_url": cover_image_url,
        "open_to_work": bool(entity.get("openToWork") or entity.get("industryOpenToWork")),
        "follower_count": entity.get("followersCount"),
    }


def parse_basic_profile_from_html(soup: BeautifulSoup) -> dict[str, Any]:
    """Extract profile fields from LinkedIn's mobile-rendered profile HTML.

    Confirmed against a live authenticated fetch: requesting a normal
    `linkedin.com/in/<slug>/` URL with a mobile User-Agent (see
    `fetcher.py`) makes LinkedIn server-render the entire visible profile -
    name, headline, location, current company, cover/profile photos, and
    the follower count - as plain semantic HTML (`<h1>`, distinctly-classed
    `<div>`s), not a client-side-only React shell. This is a completely
    different, far more reliable markup shape than LinkedIn's desktop page,
    which only renders a "top card" preview (see git history / README
    section 5 for that superseded approach).
    """
    result: dict[str, Any] = {}

    top_card = _parse_top_card(soup)
    result.update({k: v for k, v in top_card.items() if v})

    cover_url = _image_by_aria_label(soup, "Member Background Photo")
    if cover_url:
        result["cover_image_url"] = cover_url

    profile_url = _profile_photo_url(soup)
    if profile_url:
        result["profile_image_url"] = profile_url

    follower_count = _follower_count(soup)
    if follower_count is not None:
        result["follower_count"] = follower_count

    about = _about_text(soup)
    if about:
        result["about"] = about

    if not result.get("name"):
        # Last-resort fallback if even the top card wasn't found (e.g. an
        # auth-wall/anonymous page): whatever <title>/meta tags give us.
        title_name = _extract_name_from_title(soup)
        if title_name:
            result["name"] = title_name

        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description and meta_description.get("content"):
            result.setdefault("headline", meta_description["content"].strip())

        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            result.setdefault("profile_image_url", og_image["content"].strip())

    return result


def _extract_name_from_title(soup: BeautifulSoup) -> Optional[str]:
    if not soup.title or not soup.title.string:
        return None
    title = soup.title.string.strip()
    if not title or title.lower() in ("linkedin", "profile | linkedin"):
        return None
    cleaned = title.split(" | LinkedIn")[0].split(" - LinkedIn")[0].strip()
    return cleaned or None


def _parse_top_card(soup: BeautifulSoup) -> dict[str, Any]:
    container = soup.find("section", class_="basic-profile-section")
    if container is None:
        return {}

    result: dict[str, Any] = {}

    h1 = container.find("h1")
    if h1:
        name = clean_text(h1.get_text())
        if name:
            result["name"] = name

    body_small_divs = container.find_all("div", class_="body-small")

    def classes(tag: Tag) -> list[str]:
        return tag.get("class") or []

    headline_div = next(
        (d for d in body_small_divs if "text-color-text-low-emphasis" not in classes(d)),
        None,
    )
    if headline_div:
        headline = clean_text(headline_div.get_text())
        if headline:
            result["headline"] = headline

    low_emphasis_divs = [d for d in body_small_divs if "text-color-text-low-emphasis" in classes(d)]

    company_div = next((d for d in low_emphasis_divs if d.find(class_="member-current-company")), None)
    location_div = next((d for d in low_emphasis_divs if d is not company_div), None)
    if location_div:
        location = direct_text(location_div)
        if location:
            result["location"] = location

    return result


def _image_by_aria_label(soup: BeautifulSoup, aria_label: str) -> Optional[str]:
    img = soup.find("img", attrs={"aria-label": aria_label})
    if img is None:
        return None
    return img.get("data-delayed-url") or img.get("src")


def _profile_photo_url(soup: BeautifulSoup) -> Optional[str]:
    container = soup.find(id="profile-picture-container")
    if container is None:
        return None
    img = container.find("img")
    if img is None:
        return None
    return img.get("data-delayed-url") or img.get("src")


def _about_text(soup: BeautifulSoup) -> Optional[str]:
    section = soup.find("section", class_="about-section")
    if section is None:
        return None
    description = section.find("div", class_="description")
    if description is None:
        return None
    text = clean_text(description.get_text(" "))
    return text or None


def _follower_count(soup: BeautifulSoup) -> Optional[int]:
    section = soup.find("section", class_="activity-section")
    if section is None:
        return None
    text = section.get_text(" ", strip=True)
    match = re.search(r"([\d,]+)\s*followers", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None
