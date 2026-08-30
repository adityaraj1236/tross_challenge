from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup, Tag


def find_accomplishment_subsection(soup: BeautifulSoup, heading_text: str) -> Optional[Tag]:
    """Find the <ul> for an "Accomplishments" subsection (Certifications,
    Languages, Honors, Projects, ...) by its <h3> heading text.

    LinkedIn's mobile-rendered profile groups several optional sections
    under one `accomplishments-section` container, each introduced by an
    `<h3>` and followed by a `<ul>` of `sub-list-item` entries. Only
    Certifications and Languages were present on the profile this was
    developed against, so Honors/Projects/Volunteer/Publications/Courses
    below follow the same observed pattern but are unverified against a
    real example - they degrade to an empty list rather than raising if the
    shape doesn't match.
    """
    container = soup.find("section", class_="accomplishments-section")
    if container is None:
        return None

    heading = next(
        (h3 for h3 in container.find_all("h3") if h3.get_text(strip=True) == heading_text),
        None,
    )
    if heading is None:
        return None

    return heading.find_next_sibling("ul")
