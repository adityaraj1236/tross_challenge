from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from .date_utils import compute_duration, format_time_period
from .dom_utils import clean_text, exact_class_divs, split_date_range, split_on_dot_separator
from .entity_graph import EntityGraph, find_by_type_suffix, first_present, resolve
from .images import extract_vector_image_url

_POSITION_TYPE_SUFFIXES = ("identity.profile.Position",)


def parse_experience(graph: EntityGraph) -> list[dict[str, Any]]:
    """Defensive first attempt against a normalized JSON graph (see profile.py) -
    not the mechanism this implementation relies on in practice."""
    positions = find_by_type_suffix(graph, *_POSITION_TYPE_SUFFIXES)
    items: list[dict[str, Any]] = []

    for position in positions:
        mini_company = _resolve_mini_company(graph, position)

        start_date, end_date = format_time_period(position.get("timePeriod"))
        company_name = first_present(position, "companyName") or (
            first_present(mini_company, "name") if isinstance(mini_company, dict) else None
        )
        company_logo_url = extract_vector_image_url(
            (mini_company or {}).get("logo") if isinstance(mini_company, dict) else None
        )
        company_public_id = (mini_company or {}).get("universalName") if isinstance(mini_company, dict) else None

        item = {
            "title": first_present(position, "title"),
            "company": company_name,
            "company_linkedin_url": (
                f"https://www.linkedin.com/company/{company_public_id}/" if company_public_id else None
            ),
            "company_logo_url": company_logo_url,
            "employment_type": first_present(position, "employmentType", "workRemoteAllowed"),
            "location": first_present(position, "locationName", "geoLocationName"),
            "start_date": start_date,
            "end_date": end_date,
            "duration": compute_duration(start_date, end_date),
            "description": first_present(position, "description"),
        }

        if any(v for k, v in item.items() if k in ("title", "company")):
            items.append(item)

    return items


def _resolve_mini_company(graph: EntityGraph, position: dict[str, Any]) -> dict[str, Any] | None:
    company_entity = resolve(graph, position.get("*company")) or position.get("company")
    if not isinstance(company_entity, dict):
        return None
    if "name" in company_entity or "logo" in company_entity:
        return company_entity
    nested = company_entity.get("miniCompany")
    return nested if isinstance(nested, dict) else None


def parse_experience_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract the full Experience list from LinkedIn's mobile-rendered HTML.

    Confirmed against a live fetch to contain every position (no
    "Show all" truncation observed), unlike the desktop page. See
    README section 5 and `fetcher.py` for why a mobile User-Agent matters.
    """
    section = soup.find("section", class_="experience-container")
    if section is None:
        return []

    items: list[dict[str, Any]] = []
    for heading in section.find_all("div", class_="list-item-heading"):
        item = _parse_entry(heading)
        if item:
            items.append(item)
    return items


def _parse_entry(heading: Tag) -> dict[str, Any] | None:
    content = heading.parent
    if content is None:
        return None

    title = clean_text(heading.get_text())

    body_smalls = exact_class_divs(content, "body-small")
    company = clean_text(body_smalls[0].get_text()) if body_smalls else None

    start_date = end_date = duration = None
    if len(body_smalls) > 1:
        spans = body_smalls[1].find_all("span", recursive=False)
        date_text, duration = split_on_dot_separator(spans)
        start_date, end_date = split_date_range(date_text)

    location_div = content.find("div", class_="text-xs")
    location = clean_text(location_div.get_text()) if location_div else None

    description_div = content.find(attrs={"data-truncated-control": True})
    description = None
    if description_div:
        text_div = description_div.find("div", class_="description")
        if text_div:
            description = clean_text(text_div.get_text(" ")) or None

    link = content.find_parent("a")
    company_linkedin_url = link.get("href", "").split("?")[0] if link else None
    logo_img = link.find("img") if link else None
    company_logo_url = (logo_img.get("data-delayed-url") or logo_img.get("src")) if logo_img else None

    if not title and not company:
        return None

    return {
        "title": title or None,
        "company": company or None,
        "company_linkedin_url": company_linkedin_url or None,
        "company_logo_url": company_logo_url,
        "employment_type": None,
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "duration": duration or compute_duration(start_date, end_date),
        "description": description,
    }
