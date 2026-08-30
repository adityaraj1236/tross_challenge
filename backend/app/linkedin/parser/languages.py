from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from .dom_utils import clean_text
from .entity_graph import EntityGraph, find_by_type_suffix, first_present
from .additional_sections_html import find_accomplishment_subsection

_LANGUAGE_TYPE_SUFFIXES = ("identity.profile.Language",)


def parse_languages(graph: EntityGraph) -> list[dict[str, Any]]:
    """Defensive first attempt against a normalized JSON graph - see profile.py."""
    entries = find_by_type_suffix(graph, *_LANGUAGE_TYPE_SUFFIXES)
    items: list[dict[str, Any]] = []

    for entry in entries:
        name = first_present(entry, "name")
        if not name:
            continue
        items.append({
            "name": name,
            "proficiency": first_present(entry, "proficiency"),
        })

    return items


def parse_languages_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract the full Languages list from LinkedIn's mobile-rendered HTML.

    Confirmed against a live fetch to match the profile's full language
    count exactly. Proficiency level is not shown at this list-view level,
    so `proficiency` is always None.
    """
    ul = find_accomplishment_subsection(soup, "Languages")
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
        items.append({"name": name, "proficiency": None})

    return items
