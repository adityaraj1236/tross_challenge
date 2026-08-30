from __future__ import annotations

import re
from typing import Optional

from bs4 import Tag

_WS_RE = re.compile(r"\s+")


def clean_text(text: Optional[str]) -> str:
    """Collapse internal whitespace/newlines from server-rendered markup into single spaces."""
    return _WS_RE.sub(" ", text or "").strip()


def exact_class_divs(parent: Tag, class_name: str) -> list[Tag]:
    """Direct-child <div>s whose `class` attribute is *exactly* [class_name].

    Used to disambiguate sibling divs that share a class among other, more
    specific ones - e.g. an experience entry's company and dates divs are
    both bare `<div class="body-small">`, while its description wrapper adds
    extra classes on top of the same "body-small" token.
    """
    return [d for d in parent.find_all("div", recursive=False) if d.get("class") == [class_name]]


def direct_text(tag: Tag) -> str:
    """Text belonging directly to `tag`, ignoring text inside nested tags.

    Used for a location line like `<div>City, Country<span>500+ connections</span></div>`
    where the location itself is a bare text node sitting alongside a
    nested, unrelated `<span>`.
    """
    return clean_text("".join(c for c in tag.contents if isinstance(c, str)))


def split_on_dot_separator(spans: list[Tag]) -> tuple[str, Optional[str]]:
    """Split a list of <span> siblings around a `dot-separator` marker span.

    LinkedIn's mobile-rendered markup joins two related pieces of text (e.g.
    "date range" and "duration", or "degree" and "field of study") with an
    empty `<span class="dot-separator">` in between rather than real
    punctuation. Returns (before, after) with `after` as None if there was
    no separator.
    """
    dot_index = next(
        (i for i, s in enumerate(spans) if "dot-separator" in (s.get("class") or [])),
        None,
    )
    if dot_index is None:
        return clean_text(" ".join(s.get_text() for s in spans)), None

    before = clean_text(" ".join(s.get_text() for s in spans[:dot_index]))
    after = clean_text(" ".join(s.get_text() for s in spans[dot_index + 1:])) or None
    return before, after


def split_date_range(date_text: str) -> tuple[Optional[str], Optional[str]]:
    """Split a "Start - End" display string into (start, end); "Present" -> None end."""
    if not date_text:
        return None, None
    parts = re.split(r"\s-\s", date_text, maxsplit=1)
    start = parts[0].strip() or None
    end = parts[1].strip() if len(parts) > 1 else None
    if end and end.lower() == "present":
        end = None
    return start, end
