from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from .dom_utils import clean_text
from .entity_graph import EntityGraph, find_by_type_suffix, first_present

_SKILL_TYPE_SUFFIXES = ("identity.profile.Skill",)


def parse_skills(graph: EntityGraph) -> list[dict[str, Any]]:
    """Defensive first attempt against a normalized JSON graph - see profile.py."""
    entries = find_by_type_suffix(graph, *_SKILL_TYPE_SUFFIXES)
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    for entry in entries:
        name = first_present(entry, "name")
        if not name or name in seen:
            continue
        seen.add(name)
        items.append({
            "name": name,
            "endorsement_count": entry.get("endorsementCount"),
        })

    return items


def parse_skills_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract the full Skills list from LinkedIn's mobile-rendered HTML.

    Confirmed against a live fetch to match the profile's full skill count
    exactly (no truncation) - see README section 5. No endorsement counts
    are shown at this list-view level, so `endorsement_count` is always None.
    """
    section = soup.find("section", class_="skills-container")
    if section is None:
        return []

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for li in section.find_all("li", class_="skill-item"):
        span = li.find("span")
        if span is None:
            continue
        name = clean_text(span.get_text())
        if not name or name in seen:
            continue
        seen.add(name)
        items.append({"name": name, "endorsement_count": None})

    return items
