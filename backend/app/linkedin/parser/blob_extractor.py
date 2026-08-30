from __future__ import annotations

import json
from typing import Any, Iterable

from bs4 import BeautifulSoup

from ...logging_config import get_logger

logger = get_logger(__name__)


def extract_json_blobs(html: str) -> list[dict[str, Any]]:
    """Pull the embedded JSON payloads out of a LinkedIn page's HTML.

    LinkedIn server-renders the profile's data graph into hidden
    `<code>` tags so its client-side app can hydrate without an extra
    network round trip. We read those tags directly with BeautifulSoup -
    no JavaScript is executed, nothing is rendered, no browser exists.
    """
    soup = BeautifulSoup(html, "lxml")
    blobs: list[dict[str, Any]] = []

    for tag in soup.find_all("code"):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        raw = raw.strip()
        if len(raw) < 20 or raw[0] not in "{[":
            continue
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            blobs.append(parsed)
        elif isinstance(parsed, list):
            blobs.extend(item for item in parsed if isinstance(item, dict))

    logger.debug("Extracted %d JSON blob(s) from page", len(blobs))
    return blobs


def merge_entity_graph(blobs: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Merge every blob's `included` array into one entityUrn -> entity map.

    This mirrors LinkedIn's normalized ("Voyager") data shape: entities
    reference each other by URN instead of nesting, so callers resolve
    references through this graph. Later blobs win on key collisions,
    since detail sub-pages (fetched after the main profile page) tend to
    carry more complete data for their section.
    """
    graph: dict[str, dict[str, Any]] = {}
    for blob in blobs:
        included = blob.get("included")
        if not isinstance(included, list):
            continue
        for entity in included:
            if not isinstance(entity, dict):
                continue
            urn = entity.get("entityUrn")
            if not urn:
                continue
            graph[urn] = entity
    return graph
