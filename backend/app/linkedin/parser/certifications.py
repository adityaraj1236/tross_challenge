from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from .date_utils import format_date
from .dom_utils import clean_text
from .entity_graph import EntityGraph, find_by_type_suffix, first_present
from .additional_sections_html import find_accomplishment_subsection

_CERTIFICATION_TYPE_SUFFIXES = ("identity.profile.Certification",)


def parse_certifications(graph: EntityGraph) -> list[dict[str, Any]]:
    """Defensive first attempt against a normalized JSON graph - see profile.py."""
    entries = find_by_type_suffix(graph, *_CERTIFICATION_TYPE_SUFFIXES)
    items: list[dict[str, Any]] = []

    for entry in entries:
        time_period = entry.get("timePeriod")
        item = {
            "name": first_present(entry, "name"),
            "issuing_organization": first_present(entry, "authority"),
            "issue_date": format_date(time_period.get("startDate")) if isinstance(time_period, dict) else None,
            "credential_id": first_present(entry, "licenseNumber"),
            "credential_url": first_present(entry, "url"),
        }
        if item["name"]:
            items.append(item)

    return items


def parse_certifications_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract the full Certifications list from LinkedIn's mobile-rendered HTML.

    Confirmed against a live fetch to match the profile's full certification
    count exactly. Only name + issuing organization are consistently present
    at this list-view level - issue date/credential ID are not shown here.
    """
    ul = find_accomplishment_subsection(soup, "Certifications")
    if ul is None:
        return []

    items: list[dict[str, Any]] = []
    for li in ul.find_all("li", class_="sub-list-item", recursive=False):
        heading = li.find("div", class_="list-item-heading")
        if heading is None:
            continue
        name = clean_text(heading.get_text())
        if not name:
            continue

        issuer = None
        detail = li.find("div", class_="description")
        if detail:
            issuer = clean_text(detail.get_text(" ")) or None

        items.append({
            "name": name,
            "issuing_organization": issuer,
            "issue_date": None,
            "credential_id": None,
            "credential_url": None,
        })

    return items
