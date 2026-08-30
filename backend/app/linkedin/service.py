from __future__ import annotations

from bs4 import BeautifulSoup

from ..config import Settings
from ..logging_config import get_logger, log_with_context
from .exceptions import LinkedInParseError
from .fetcher import LinkedInFetcher
from .parser.additional_sections import (
    parse_courses,
    parse_courses_from_html,
    parse_honors,
    parse_honors_from_html,
    parse_interests,
    parse_interests_from_html,
    parse_projects,
    parse_projects_from_html,
    parse_publications,
    parse_publications_from_html,
    parse_volunteer_experience,
    parse_volunteer_experience_from_html,
)
from .parser.blob_extractor import extract_json_blobs, merge_entity_graph
from .parser.certifications import parse_certifications, parse_certifications_from_html
from .parser.education import parse_education, parse_education_from_html
from .parser.experience import parse_experience, parse_experience_from_html
from .parser.languages import parse_languages, parse_languages_from_html
from .parser.profile import parse_basic_profile, parse_basic_profile_from_html
from .parser.skills import parse_skills, parse_skills_from_html
from .schemas import ProfileData, ProfileResponse
from .url_utils import parse_profile_url

logger = get_logger(__name__)


class LinkedInProfileService:
    """Orchestrates fetching + parsing a LinkedIn profile into structured JSON.

    A single direct-HTTP GET of the profile URL (see `fetcher.py` for why it
    uses a mobile User-Agent) is enough: confirmed against a live
    authenticated fetch, LinkedIn server-renders the *entire* profile -
    About, the full Experience/Education/Skills/Certifications/Languages
    lists, not just a preview - into that one response when requested this
    way. No `/details/<section>/` sub-page fetching or pagination is needed
    (those routes are also actively blocked for non-browser clients - see
    README section 15).

    Extraction runs two layers per field: a defensive first attempt against
    a normalized JSON data graph (`parser/blob_extractor.py`), which
    LinkedIn does not currently embed but might again; and HTML-based
    extraction against the server-rendered DOM, which is what actually
    supplies data today. Whichever layer finds a given field wins.
    """

    def __init__(self, settings: Settings, fetcher: LinkedInFetcher | None = None):
        self._settings = settings
        self._fetcher = fetcher or LinkedInFetcher(settings)
        self._owns_fetcher = fetcher is None

    async def aclose(self) -> None:
        if self._owns_fetcher:
            await self._fetcher.aclose()

    async def get_profile(self, raw_url: str) -> ProfileResponse:
        ref = parse_profile_url(raw_url)
        log_with_context(
            logger, "INFO", "Fetching LinkedIn profile",
            context={"public_id": ref.public_id, "authenticated": self._fetcher.is_authenticated},
        )

        html = await self._fetcher.fetch_html(ref.canonical_url)
        soup = BeautifulSoup(html, "lxml")
        graph = merge_entity_graph(extract_json_blobs(html))

        warnings: list[str] = []

        basic = parse_basic_profile(graph)
        html_basic = parse_basic_profile_from_html(soup)
        basic = {**html_basic, **{k: v for k, v in basic.items() if v}}
        if not basic.get("name"):
            warnings.append(
                "Could not extract even the profile name from this page - it may be an "
                "auth-wall/anonymous view, or LinkedIn's markup has changed."
            )

        experience = parse_experience(graph) or parse_experience_from_html(soup)
        education = parse_education(graph) or parse_education_from_html(soup)
        skills = parse_skills(graph) or parse_skills_from_html(soup)
        certifications = parse_certifications(graph) or parse_certifications_from_html(soup)
        languages = parse_languages(graph) or parse_languages_from_html(soup)
        honors = parse_honors(graph) or parse_honors_from_html(soup)
        projects = parse_projects(graph) or parse_projects_from_html(soup)
        volunteer = parse_volunteer_experience(graph) or parse_volunteer_experience_from_html(soup)
        courses = parse_courses(graph) or parse_courses_from_html(soup)
        publications = parse_publications(graph) or parse_publications_from_html(soup)
        interests = parse_interests(graph) or parse_interests_from_html(soup)

        if not basic.get("name") and not experience and not education:
            raise LinkedInParseError(
                "Fetched the profile page successfully but could not extract any usable data. "
                "LinkedIn's markup/embedded-data format may have changed."
            )

        for section_name, values in (
            ("experience", experience), ("education", education), ("skills", skills),
        ):
            if not values:
                warnings.append(f"No {section_name} data was found (section may be empty, private, or truncated).")

        data = ProfileData(
            linkedin_url=ref.canonical_url,
            public_id=ref.public_id,
            experience=experience,
            education=education,
            skills=skills,
            certifications=certifications,
            languages=languages,
            honors=honors,
            projects=projects,
            volunteer_experience=volunteer,
            courses=courses,
            publications=publications,
            interests=interests,
            **{k: v for k, v in basic.items() if k in ProfileData.model_fields},
        )

        log_with_context(
            logger, "INFO", "LinkedIn profile fetched and parsed successfully",
            context={
                "public_id": ref.public_id,
                "experience_count": len(experience),
                "education_count": len(education),
                "skills_count": len(skills),
                "warning_count": len(warnings),
            },
        )

        return ProfileResponse(data=data, partial=bool(warnings), warnings=warnings)
