from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from .date_utils import format_time_period
from .dom_utils import clean_text, split_date_range, split_on_dot_separator
from .entity_graph import EntityGraph, find_by_type_suffix, first_present, resolve
from .images import extract_vector_image_url

_EDUCATION_TYPE_SUFFIXES = ("identity.profile.Education",)


def parse_education(graph: EntityGraph) -> list[dict[str, Any]]:
    """Defensive first attempt against a normalized JSON graph - see profile.py."""
    entries = find_by_type_suffix(graph, *_EDUCATION_TYPE_SUFFIXES)
    items: list[dict[str, Any]] = []

    for entry in entries:
        school_entity = resolve(graph, entry.get("*school")) or entry.get("school") or {}
        start_date, end_date = format_time_period(entry.get("timePeriod"))

        institution_name = first_present(entry, "schoolName") or (
            first_present(school_entity, "name") if isinstance(school_entity, dict) else None
        )
        institution_logo_url = extract_vector_image_url(
            (school_entity or {}).get("logo") if isinstance(school_entity, dict) else None
        )
        institution_public_id = (
            (school_entity or {}).get("universalName") if isinstance(school_entity, dict) else None
        )

        item = {
            "institution": institution_name,
            "institution_linkedin_url": (
                f"https://www.linkedin.com/school/{institution_public_id}/" if institution_public_id else None
            ),
            "institution_logo_url": institution_logo_url,
            "degree": first_present(entry, "degreeName"),
            "field_of_study": first_present(entry, "fieldOfStudy"),
            "start_date": start_date,
            "end_date": end_date,
            "description": first_present(entry, "description", "activities", "notes"),
        }

        if any(v for k, v in item.items() if k in ("institution", "degree")):
            items.append(item)

    return items


def parse_education_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract the full Education list from LinkedIn's mobile-rendered HTML."""
    section = soup.find("section", class_="education-container")
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

    institution = clean_text(heading.get_text())

    body_smalls = [
        d for d in content.find_all("div", recursive=False)
        if d.get("class") and "body-small" in d.get("class") and d is not heading
    ]

    degree = field_of_study = None
    if body_smalls:
        spans = body_smalls[0].find_all("span", recursive=False)
        degree, field_of_study = split_on_dot_separator(spans)

    start_date = end_date = None
    if len(body_smalls) > 1:
        spans = body_smalls[1].find_all("span", recursive=False)
        date_text, _ = split_on_dot_separator(spans)
        start_date, end_date = split_date_range(date_text)

    link = content.find_parent("a")
    institution_linkedin_url = link.get("href", "").split("?")[0] if link else None
    logo_img = link.find("img") if link else None
    institution_logo_url = (logo_img.get("data-delayed-url") or logo_img.get("src")) if logo_img else None

    if not institution and not degree:
        return None

    return {
        "institution": institution or None,
        "institution_linkedin_url": institution_linkedin_url or None,
        "institution_logo_url": institution_logo_url,
        "degree": degree or None,
        "field_of_study": field_of_study,
        "start_date": start_date,
        "end_date": end_date,
        "description": None,
    }
