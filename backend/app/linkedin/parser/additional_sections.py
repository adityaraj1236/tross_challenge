from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from .additional_sections_html import find_accomplishment_subsection
from .date_utils import format_time_period
from .dom_utils import clean_text
from .entity_graph import EntityGraph, find_by_type_suffix, first_present, resolve

# Best-effort, lower-priority profile sections. LinkedIn omits most of these
# for the majority of profiles, so an empty list here is the normal case,
# not a parsing failure.


def parse_honors(graph: EntityGraph) -> list[dict[str, Any]]:
    entries = find_by_type_suffix(graph, "identity.profile.Honor")
    items = []
    for entry in entries:
        items.append({
            "title": first_present(entry, "title"),
            "issuer": first_present(entry, "issuer"),
            "issue_date": _start_date(entry),
            "description": first_present(entry, "description"),
        })
    return [i for i in items if i["title"]]


def parse_projects(graph: EntityGraph) -> list[dict[str, Any]]:
    entries = find_by_type_suffix(graph, "identity.profile.Project")
    items = []
    for entry in entries:
        start, end = format_time_period(entry.get("timePeriod"))
        items.append({
            "name": first_present(entry, "title", "name"),
            "description": first_present(entry, "description"),
            "url": first_present(entry, "url"),
            "start_date": start,
            "end_date": end,
        })
    return [i for i in items if i["name"]]


def parse_volunteer_experience(graph: EntityGraph) -> list[dict[str, Any]]:
    entries = find_by_type_suffix(graph, "identity.profile.VolunteerExperience")
    items = []
    for entry in entries:
        company_entity = resolve(graph, entry.get("*company")) or {}
        start, end = format_time_period(entry.get("timePeriod"))
        items.append({
            "organization": first_present(entry, "companyName") or first_present(company_entity, "name"),
            "role": first_present(entry, "role"),
            "cause": first_present(entry, "cause"),
            "start_date": start,
            "end_date": end,
            "description": first_present(entry, "description"),
        })
    return [i for i in items if i["organization"] or i["role"]]


def parse_courses(graph: EntityGraph) -> list[dict[str, Any]]:
    entries = find_by_type_suffix(graph, "identity.profile.Course")
    items = []
    for entry in entries:
        items.append({
            "name": first_present(entry, "name"),
            "number": first_present(entry, "number"),
        })
    return [i for i in items if i["name"]]


def parse_publications(graph: EntityGraph) -> list[dict[str, Any]]:
    entries = find_by_type_suffix(graph, "identity.profile.Publication")
    items = []
    for entry in entries:
        items.append({
            "title": first_present(entry, "name", "title"),
            "publisher": first_present(entry, "publisher"),
            "publish_date": _start_date(entry),
            "description": first_present(entry, "description"),
            "url": first_present(entry, "url"),
        })
    return [i for i in items if i["title"]]


def parse_interests(graph: EntityGraph) -> list[str]:
    entries = find_by_type_suffix(
        graph, "identity.profile.Interest", "identity.profile.SavedCompany", "identity.profile.Influencer"
    )
    names = []
    for entry in entries:
        name = first_present(entry, "name", "title")
        if name and name not in names:
            names.append(name)
    return names


def _start_date(entry: dict[str, Any]) -> str | None:
    time_period = entry.get("timePeriod")
    if not isinstance(time_period, dict):
        return None
    start, _end = format_time_period(time_period)
    return start


# --- HTML-based extraction (see profile.py for why this is the primary path) ---
#
# Honors/Projects/Volunteer experience/Publications/Courses were not present
# on the profile this parser was developed against, so these follow the same
# `sub-list-item` pattern confirmed for Certifications/Languages but are
# unverified against a real example. Each degrades to an empty list - never
# raises - if the assumed shape doesn't match.

def _simple_name_list_from_html(soup: BeautifulSoup, heading_text: str) -> list[str]:
    ul = find_accomplishment_subsection(soup, heading_text)
    if ul is None:
        return []
    names = []
    for li in ul.find_all("li", class_="sub-list-item", recursive=False):
        heading = li.find("div", class_="list-item-heading")
        if heading is None:
            continue
        name = clean_text(heading.get_text())
        if name:
            names.append(name)
    return names


def parse_honors_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    return [
        {"title": title, "issuer": None, "issue_date": None, "description": None}
        for title in _simple_name_list_from_html(soup, "Honors & awards")
    ]


def parse_projects_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    return [
        {"name": name, "description": None, "url": None, "start_date": None, "end_date": None}
        for name in _simple_name_list_from_html(soup, "Projects")
    ]


def parse_volunteer_experience_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    return [
        {
            "organization": name, "role": None, "cause": None,
            "start_date": None, "end_date": None, "description": None,
        }
        for name in _simple_name_list_from_html(soup, "Volunteering")
    ]


def parse_courses_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    return [{"name": name, "number": None} for name in _simple_name_list_from_html(soup, "Courses")]


def parse_publications_from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    return [
        {"title": title, "publisher": None, "publish_date": None, "description": None, "url": None}
        for title in _simple_name_list_from_html(soup, "Publications")
    ]


def parse_interests_from_html(soup: BeautifulSoup) -> list[str]:
    return _simple_name_list_from_html(soup, "Interests")
