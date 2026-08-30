from __future__ import annotations

from typing import Any, Optional


def extract_vector_image_url(value: Any) -> Optional[str]:
    """Resolve a LinkedIn `VectorImage` (rootUrl + size artifacts) to one URL.

    LinkedIn images are shipped as a root CDN URL plus a list of artifacts,
    one per rendered size; we pick the widest available artifact. The
    VectorImage dict is sometimes the value itself and sometimes nested one
    level under a `$type` discriminator key, so both shapes are handled.
    """
    candidate = _find_vector_image_dict(value)
    if not candidate:
        return None

    root_url = candidate.get("rootUrl")
    artifacts = candidate.get("artifacts") or []
    if not root_url or not artifacts:
        return None

    def artifact_width(artifact: Any) -> int:
        return artifact.get("width", 0) if isinstance(artifact, dict) else 0

    best = max(artifacts, key=artifact_width)
    if not isinstance(best, dict):
        return None

    segment = best.get("fileIdentifyingUrlPathSegment")
    if not segment:
        return None

    return f"{root_url}{segment}"


def largest_from_srcset(srcset: Optional[str]) -> Optional[str]:
    """Pick the widest image URL out of an `<img srcset>` attribute.

    LinkedIn's server-rendered `<img>` tags ship a standard responsive
    `srcset` ("url1 100w, url2 400w, url3 800w"); we want the highest-
    resolution variant.
    """
    if not srcset:
        return None

    best_url: Optional[str] = None
    best_width = -1
    for candidate in srcset.split(","):
        parts = candidate.strip().split()
        if not parts:
            continue
        url = parts[0]
        width = 0
        if len(parts) > 1 and parts[1].endswith("w"):
            try:
                width = int(parts[1][:-1])
            except ValueError:
                width = 0
        if width >= best_width:
            best_width = width
            best_url = url

    return best_url


def _find_vector_image_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    if "rootUrl" in value and "artifacts" in value:
        return value
    for nested in value.values():
        if isinstance(nested, dict) and "rootUrl" in nested and "artifacts" in nested:
            return nested
    return None
