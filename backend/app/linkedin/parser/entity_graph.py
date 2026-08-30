from __future__ import annotations

from typing import Any, Iterable, Optional

EntityGraph = dict[str, dict[str, Any]]


def type_name(entity: dict[str, Any]) -> str:
    return str(entity.get("$type", ""))


def find_by_type_suffix(graph: EntityGraph, *suffixes: str) -> list[dict[str, Any]]:
    """Return every entity whose `$type` ends with one of the given suffixes.

    LinkedIn's internal types are fully-qualified, e.g.
    `com.linkedin.voyager.identity.profile.Position`. Matching by suffix is
    resilient to the `com.linkedin.voyager...` package prefix, which has
    changed across LinkedIn API generations.
    """
    out = []
    for entity in graph.values():
        t = type_name(entity)
        if any(t.endswith(suffix) for suffix in suffixes):
            out.append(entity)
    return out


def resolve(graph: EntityGraph, urn: Optional[str]) -> Optional[dict[str, Any]]:
    if not urn:
        return None
    return graph.get(urn)


def resolve_many(graph: EntityGraph, urns: Optional[Iterable[str]]) -> list[dict[str, Any]]:
    if not urns:
        return []
    return [entity for urn in urns if (entity := graph.get(urn))]


def first_present(entity: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value among several candidate field names.

    Used defensively throughout the parsers because LinkedIn's field naming
    has drifted between API generations (e.g. `locationName` vs `geoLocationName`).
    """
    for key in keys:
        value = entity.get(key)
        if value not in (None, "", []):
            return value
    return None
