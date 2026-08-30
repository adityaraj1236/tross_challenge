# LinkedIn Profile API

A hosted API that accepts a LinkedIn profile URL and returns structured JSON
covering name, headline, location, about, experience, education, skills,
certifications, languages, and profile images. Built for the Tross Software
Engineer hiring challenge.

**This service never launches a browser.** Every request to LinkedIn is a
direct HTTP call made with `httpx`. This was a hard requirement clarified after the original brief: *"we are looking for a purely
reverse-engineered solution that directly hits LinkedIn endpoints and does
not use a browser."*

---

## 1. Project overview

- **Backend:** FastAPI (Python), exposes `POST /api/linkedin/profile` and `GET /health`.
- **Frontend:** Next.js (TypeScript, Tailwind), a single-page form that calls the backend and renders the result.
- **LinkedIn access:** one direct `httpx` GET per profile, using a cookie-based session (your own LinkedIn account) and a mobile User-Agent - no Selenium/Playwright/Puppeteer/Chromium anywhere in the stack.

## 2. Challenge interpretation

The original brief's example flow (`GET https://www.linkedin.com/in/<slug>/`)
suggested reading the profile page's HTML directly. The follow-up
clarification email made the constraint explicit: no browser, direct HTTP to
LinkedIn's own endpoints only. This repo implements exactly that - and,
importantly, it was *tuned against a live authenticated fetch* rather than
left as a guess: the request shape that actually works (documented in
section 5) was discovered by fetching a real profile, inspecting exactly
what LinkedIn sent back, and adjusting until the response matched what a
real browser shows.

## 3. Architecture

```
                ┌────────────────────┐
                │     Next.js UI     │
                │  Simple frontend   │
                └─────────┬──────────┘
                          │ HTTP (JSON)
                          ▼
                ┌────────────────────┐
                │   FastAPI Backend  │
                │  POST /api/linkedin│
                │       /profile     │
                └─────────┬──────────┘
                          │ ONE httpx GET (direct HTTP, cookie auth,
                          │ mobile User-Agent - see section 5)
                          ▼
                ┌────────────────────┐
                │     linkedin.com    │
                │     /in/<slug>/      │
                └────────────────────┘
```

No browser exists anywhere in this flow - not in the backend, not in a
sidecar process, not as a fallback. A single request per profile is all
that's needed; there's no follow-up call to any `/details/<section>/`
sub-page (see section 5 for why).

Backend module layout:

```
backend/app/
  main.py                 FastAPI app, CORS, lifespan logging
  config.py                Settings (env vars only, no hardcoded secrets)
  logging_config.py        Structured logging with credential redaction
  api/routes.py            POST /api/linkedin/profile, GET /health
  linkedin/
    fetcher.py              httpx client: cookies, mobile UA, response classification
    url_utils.py             Profile URL validation + slug extraction
    exceptions.py            Typed LinkedIn errors -> HTTP status mapping
    schemas.py                Pydantic request/response models
    service.py                 Orchestrates fetch -> parse -> ProfileResponse
    parser/
      profile.py                Top-card fields (name/headline/location/images/about)
      experience.py, education.py, skills.py,
      certifications.py, languages.py, additional_sections.py
                                  Section parsers against the mobile-rendered DOM
      additional_sections_html.py  Shared "Accomplishments" subsection finder (h3 -> <ul>)
      dom_utils.py               Shared HTML-parsing helpers (clean_text, dot-separator split, ...)
      date_utils.py              Date formatting for the JSON-graph fallback path
      blob_extractor.py          Defensive fallback: extracts embedded JSON, if any
      entity_graph.py            URN-indexed lookup over that JSON graph
      images.py                  VectorImage/srcset resolution helpers
```

## 4. Why the implementation is browserless

Every LinkedIn request is a single plain `httpx.AsyncClient.get()` call.
Session state is a cookie (`li_at`, optionally `JSESSIONID`) supplied via
environment variables - never a Selenium/Playwright/Puppeteer session, never
a headless Chromium process. `requirements.txt` intentionally contains no
browser automation package.

## 5. Direct HTTP / reverse-engineering approach

This is the part of the challenge that actually required reverse
engineering, and it went through two iterations - both driven by testing
against a real, authenticated LinkedIn fetch rather than assumption.

**Iteration 1 (didn't hold up): an embedded JSON data graph.** Older
writeups of LinkedIn's architecture describe profile pages server-rendering
their data as JSON in hidden `<code>` tags (LinkedIn's internal "Voyager"
shape - entities tagged with `$type`, linked by `entityUrn`). The fetcher and
parser were first built around extracting that
(`parser/blob_extractor.py`, `entity_graph.py`). Against a live fetch this
data graph doesn't exist in the HTML at all - zero `<code>` tags, zero
`$type`/`included` occurrences. That code is kept as a harmless defensive
first attempt in case it varies by locale/experiment, but it found nothing
in testing and is not what this implementation actually relies on.

**Iteration 2 (also incomplete): parsing the desktop page's DOM.** The
desktop `linkedin.com/in/<slug>/` page (default `httpx` request, desktop
User-Agent) *does* server-render real name/headline/location/photo content
into real HTML - just with obfuscated CSS classes. But the full itemized
Experience/Education/Skills/Certifications/Languages lists and the About
text are **not present in that HTML at all** - only a one-line "Company ·
School" summary is. LinkedIn loads those sections via a client-side data
fetch that fires after the page's own JavaScript executes, which no
HTTP-only client can observe or trigger.

**What actually works, confirmed against a live fetch: request the same
`linkedin.com/in/<slug>/` URL with a mobile Chrome User-Agent and matching
`sec-ch-ua-mobile`/`sec-ch-ua-platform` client hints** (see
`fetcher.py`'s `_DEFAULT_USER_AGENT` and `_MOBILE_CLIENT_HINT_HEADERS`).
LinkedIn responds with a *completely different, ~180KB, fully
server-rendered* page instead of the ~1MB desktop React shell - and that
page contains the entire profile: About, and every item in Experience,
Education, Skills, Certifications, and Languages, in clean, distinctly-
classed semantic HTML (`<h1 class="heading-large">`, `list-item-heading`,
`skill-item`, `sub-list-item`, etc. - see `parser/dom_utils.py` and the
section parsers for the exact selectors). This was verified end-to-end
against a real profile: the parsed output matched the profile's real
Experience count, Education, and *exactly* its real Skills count (45/45)
and Certifications count (8/8). No `/details/<section>/` sub-page requests
are needed at all - one request returns everything.

**Why a User-Agent switch counts as "direct HTTP," not a workaround:**
nothing about this bypasses authentication, solves a challenge, or touches
data the account isn't authorized to see - it's the same authenticated
session, the same URL, over plain HTTP. It's the discovery that LinkedIn's
own server picks a different (and, for this purpose, more complete)
rendering path based on a request header a browser sends anyway. Every
selector in `parser/*.py` was derived by inspecting that real response, not
guessed at from documentation.

**Authentication is required for anything at all.** Without a valid `li_at`
session cookie, LinkedIn serves an auth-wall page; this is treated as a
normal, typed error (`AUTH_REQUIRED`), never bypassed.

**What we deliberately do not do:** solve CAPTCHAs, bypass security
checkpoints, use anyone else's session, spoof TLS/browser fingerprints, or
retry past a challenge page. If LinkedIn returns a checkpoint/CAPTCHA, the
API returns `CHALLENGE_REQUIRED` and stops. LinkedIn's `/details/<section>/`
sub-pages were found to reject direct-HTTP requests outright with an
infinite self-redirect during testing (irrelevant now that they're unused,
but documented in section 15 since the fetcher's redirect-loop handling
exists because of it) - that is surfaced as `BLOCKED_BY_LINKEDIN` and never
retried, since retrying a deterministic loop only adds load against
LinkedIn for no benefit.

## 6. Existing-codebase learnings

This repo was designed after inspecting an existing, unrelated
Playwright-based LinkedIn scraper in this environment
(`social_media_data_extraction/linkedin_scraper/`). That code was reused
**only as a reference for domain knowledge**, not copied:

- Its `Person`/`Experience`/`Education` Pydantic models
  (`company_scraper/models.py`) informed this repo's response schema field
  choices.
- Its `BrowserManager` (`company_scraper/browser.py`) is the browser-dependent
  piece being intentionally replaced end-to-end: `storage_state`-based
  cookie/session loading is the *only* idea carried forward - as plain
  `httpx` cookies here, with no Chromium/Playwright involved.
- Its DOM-based selectors (e.g. `div[componentkey^="entity-collection-item"]`,
  `div[componentkey^="com.linkedin.sdui.profile.skill("]`) only exist in the
  post-hydration desktop DOM after Playwright executes LinkedIn's
  JavaScript - confirmed unusable directly, since a plain HTTP fetch of the
  desktop page never reaches that state. This is exactly why this
  implementation instead targets LinkedIn's mobile-rendered response (see
  section 5), which server-renders full section data without needing any
  JavaScript execution at all.

## 7. Setup

Prerequisites: Python 3.11+, Node.js 18+.

```bash
git clone <this-repo>
cd tross_Challenge
```

## 8. Environment variables

Backend (`backend/.env`, copy from `backend/.env.example`):

| Variable | Required | Description |
|---|---|---|
| `LINKEDIN_LI_AT` | Yes, for real data | Your LinkedIn account's `li_at` session cookie |
| `LINKEDIN_JSESSIONID` | Optional | Your `JSESSIONID` cookie (also used as the CSRF token) |
| `LINKEDIN_EXTRA_COOKIES` | No | Additional `name=value; name2=value2` cookies if needed |
| `LINKEDIN_USER_AGENT` | No | Override the default mobile Chrome UA string (see section 5 - changing this may lose the full-section rendering) |
| `REQUEST_TIMEOUT_SECONDS` | No | Default `15` |
| `MAX_RETRIES` | No | Default `3` |
| `RETRY_BACKOFF_SECONDS` | No | Default `1.5` |
| `LOG_LEVEL` | No | Default `INFO` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins for the frontend, default `*` |

**How to get `li_at`/`JSESSIONID`:** log into linkedin.com in your own
browser, open DevTools → Application → Cookies → `https://www.linkedin.com`,
and copy the values. These are your own account's credentials - never
commit them, and rotate/remove them when you're done testing.

Frontend (`frontend/.env.local`, copy from `frontend/.env.example`):

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Base URL of the running backend, e.g. `http://localhost:8000` |

## 9. Local development

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate       # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env         # then fill in LINKEDIN_LI_AT, etc.
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Visit `http://localhost:3000`.

## 10. Backend API documentation

Interactive docs (Swagger UI) are auto-generated by FastAPI at `/docs` once
the backend is running.

### `GET /health`

Returns `{"status": "ok"}`. Used for uptime/deployment health checks.

### `POST /api/linkedin/profile`

Accepts a LinkedIn profile URL, returns structured profile data.

## 11. Request example

```bash
curl -X POST https://your-backend.example.com/api/linkedin/profile \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.linkedin.com/in/jane-doe/"}'
```

## 12. Response example

Field shapes below reflect what was actually observed parsing a real,
consenting test profile end-to-end (values replaced with fictional data).
`experience`, `education`, `skills`, `certifications`, and `languages` are
genuinely populated in normal operation now, not just illustrative - see
section 5.

```json
{
  "success": true,
  "partial": false,
  "warnings": [],
  "fetched_at": "2026-08-29T12:00:00Z",
  "data": {
    "linkedin_url": "https://www.linkedin.com/in/jane-doe/",
    "public_id": "jane-doe",
    "name": "Jane Doe",
    "headline": "Senior Software Engineer at Example Corp",
    "location": "San Francisco Bay Area",
    "about": "Backend engineer focused on distributed systems and developer tooling.",
    "open_to_work": false,
    "follower_count": 4820,
    "profile_image_url": "https://media.licdn.com/dms/image/v2/.../profile-displayphoto-shrink_400_400/...",
    "cover_image_url": "https://media.licdn.com/dms/image/v2/.../profile-displaybackgroundimage-shrink_200_800/...",
    "experience": [
      {
        "title": "Senior Software Engineer",
        "company": "Example Corp",
        "company_linkedin_url": "https://www.linkedin.com/company/example-corp",
        "company_logo_url": "https://media.licdn.com/dms/image/v2/.../company-logo_100_100/...",
        "employment_type": null,
        "location": "San Francisco, California",
        "start_date": "Mar 2022",
        "end_date": null,
        "duration": "3 yrs 6 mos",
        "description": "Leading the backend platform team; owns service infrastructure and CI/CD."
      }
    ],
    "education": [
      {
        "institution": "State University",
        "institution_linkedin_url": "https://www.linkedin.com/school/state-university/",
        "institution_logo_url": "https://media.licdn.com/dms/image/v2/.../company-logo_100_100/...",
        "degree": "B.S.",
        "field_of_study": "Computer Science",
        "start_date": "2015",
        "end_date": "2019",
        "description": null
      }
    ],
    "skills": [{ "name": "Python", "endorsement_count": null }],
    "certifications": [
      {
        "name": "AWS Certified Solutions Architect",
        "issuing_organization": "Amazon Web Services",
        "issue_date": null,
        "credential_id": null,
        "credential_url": null
      }
    ],
    "languages": [{ "name": "English", "proficiency": null }],
    "honors": [],
    "projects": [],
    "volunteer_experience": [],
    "courses": [],
    "publications": [],
    "interests": []
  }
}
```

A few fields are consistently `null` at this list-view level even when the
section itself is fully populated - `employment_type`, skill
`endorsement_count`, certification `issue_date`/`credential_id`, and
language `proficiency` are not shown in the mobile-rendered markup this
service parses (see section 15).

Error response shape (any non-2xx):

```json
{
  "success": false,
  "error_code": "AUTH_REQUIRED",
  "message": "LinkedIn redirected to a login/authwall/checkpoint page. A valid, non-expired li_at session cookie is required for this profile."
}
```

| `error_code` | HTTP status | Meaning |
|---|---|---|
| `INVALID_URL` | 400 | Not a recognizable `linkedin.com/in/...` URL |
| `AUTH_REQUIRED` | 401 | No/expired session cookie, or LinkedIn authwalled the request |
| `CHALLENGE_REQUIRED` | 403 | LinkedIn served a CAPTCHA/security checkpoint - not bypassed |
| `PROFILE_NOT_FOUND` | 404 | Profile doesn't exist / isn't public |
| `RATE_LIMITED` | 429 | LinkedIn is throttling this client |
| `BLOCKED_BY_LINKEDIN` | 403 | LinkedIn rejected the request with an infinite self-redirect (its anti-automation defense) - never retried |
| `PARSE_ERROR` / `UPSTREAM_ERROR` | 502 | Page fetched but no usable data found, or LinkedIn 5xx'd |
| `INTERNAL_ERROR` | 500 | Unexpected server-side bug |

## 13. Frontend usage

Open the app, paste a LinkedIn profile URL, click "Fetch Profile". The page
shows a loading state while the backend fetches/parses, then renders name,
headline, location, about, experience, education, skills, certifications,
and languages. Errors from the backend are surfaced with their `error_code`.

## 14. Deployment

**Backend** - any host that runs a Docker container or a Python process works:

```bash
cd backend
docker build -t linkedin-profile-api .
docker run -p 8000:8000 --env-file .env linkedin-profile-api
```

Or without Docker: `uvicorn app.main:app --host 0.0.0.0 --port 8000` behind
a reverse proxy (nginx/Caddy) terminating HTTPS. Set all environment
variables from section 8 in the host's environment, never in source control.

**Frontend** - deploy to Vercel, Netlify, or any Node host:

```bash
cd frontend
npm run build
npm start
```

Set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend's public HTTPS URL.
Set the backend's `CORS_ORIGINS` to the frontend's deployed origin.

**Render:** `render.yaml` at the repo root defines both services as a
Render Blueprint (Dashboard → New → Blueprint → point at this repo). It
provisions `tross-linkedin-api` (Python) and `tross-linkedin-frontend`
(Node) automatically, but leaves every secret and cross-service URL as
`sync: false` - nothing sensitive is in the file. After the first deploy:

1. Set `LINKEDIN_LI_AT` (and optionally `LINKEDIN_JSESSIONID`,
   `LINKEDIN_EXTRA_COOKIES`) on `tross-linkedin-api` from its Environment tab.
2. Copy `tross-linkedin-api`'s public URL, set it as `NEXT_PUBLIC_API_BASE_URL`
   on `tross-linkedin-frontend`.
3. Copy `tross-linkedin-frontend`'s public URL, set it as `CORS_ORIGINS` on
   `tross-linkedin-api`.
4. Redeploy both (Render does this automatically on env var changes).

## 15. Known limitations

Stated plainly because they were confirmed by running this service against
a real, authenticated LinkedIn fetch during development - not guessed at:

- **A handful of sub-fields are never populated, because LinkedIn's
  mobile-rendered list views don't show them.** `employment_type` on
  experience entries, `endorsement_count` on skills, `issue_date` /
  `credential_id` / `credential_url` on certifications, and `proficiency` on
  languages are consistently `null` - confirmed absent from the HTML this
  service parses, not a parsing failure. Getting these would require either
  the desktop page (which doesn't render full sections at all - see
  section 5) or a per-item detail page, which was not pursued given the
  `/details/*` route blocking described below.
- **`Honors`, `Projects`, `Volunteer experience`, `Courses`, and
  `Publications` follow an *inferred*, not directly observed, markup
  pattern.** The one real profile this was tested against only had
  Certifications and Languages under its "Accomplishments" section; the
  parsers for the other five sections
  (`parser/additional_sections.py`) assume the same `sub-list-item` shape
  by consistency with those two, but were never confirmed against a profile
  that actually has them. They degrade to an empty list rather than raising
  if the assumed shape doesn't match - worth verifying against a real
  profile with those sections before depending on them.
- **The `/details/<section>/` sub-pages are actively blocked for
  non-browser clients.** No longer relevant to normal operation (a single
  request to the profile URL now returns every section - see section 5),
  but documented because it's why the fetcher has redirect-loop handling at
  all: every attempt to fetch `/details/experience/`, `/details/education/`,
  etc. directly during testing was rejected with an infinite self-redirect -
  LinkedIn's anti-automation defense on those specific routes. This is
  surfaced as `BLOCKED_BY_LINKEDIN` and never retried.
- **Rapid repeated requests can degrade even the main profile page.**
  During development, sending roughly a dozen requests to the same profile
  within a few minutes caused LinkedIn to start redirect-looping the *main*
  page too - i.e. this client's own session got soft-blocked by its own
  test traffic, and it took logging into LinkedIn again for a fresh session
  to recover. Space out requests in real usage; this is not a bug to work
  around, it's LinkedIn's rate-limiting working as intended, and this
  service reports it as `BLOCKED_BY_LINKEDIN` rather than retrying into it.
- **A valid, non-expired `li_at` session cookie is required for anything.**
  Without one, LinkedIn serves an auth-wall and every request returns
  `AUTH_REQUIRED`.
- **LinkedIn's markup can change without notice.** The mobile-rendered
  selectors this service depends on (`heading-large`, `list-item-heading`,
  `skill-item`, `sub-list-item`, the `data-truncated-control` description
  wrapper, etc.) reflect LinkedIn's structure as reverse-engineered at the
  time of writing. If LinkedIn changes it, section parsers will need their
  selectors updated - each parser is isolated to its own small file for
  exactly this reason. Automated tests pin every parser against fixed
  sample HTML modeled on the real response, so any regression during a
  future LinkedIn change shows up immediately in CI, but no parser is
  guaranteed to survive an arbitrary redesign untouched.
- **No caching or queueing layer.** Each request re-fetches LinkedIn live;
  given how easily this session got soft-blocked during testing, a cache
  and/or request-spacing layer in front of this API would meaningfully
  reduce that risk for any real usage, but was out of scope for this
  challenge.

## 16. Error handling

- Every LinkedIn-specific failure mode is a typed exception
  (`linkedin/exceptions.py`) with a stable `error_code`, mapped to an
  appropriate HTTP status in `api/routes.py`.
- The fetcher (`linkedin/fetcher.py`) classifies every response - HTTP
  status, redirect target, redirect-loop detection, and page content -
  before returning, so authwalls/checkpoints/blocks are caught immediately
  rather than silently parsed as empty data.
- A redirect loop (`httpx.TooManyRedirects`) is never retried - it's
  deterministic, so retrying would just repeat the same loop `MAX_RETRIES`
  times for no benefit while adding load against LinkedIn.
- Unexpected exceptions are caught at the route layer and returned as a
  generic `INTERNAL_ERROR` (500) rather than leaking a stack trace to the
  client.

## 17. Security considerations

- No credentials are ever hardcoded. All LinkedIn session data comes from
  environment variables (see `.env.example`); `.gitignore` excludes `.env`
  and `.env.local` everywhere in the repo.
- Logging (`logging_config.py`) redacts cookie/authorization/session-shaped
  keys before anything is written out, so a session cookie can never end up
  in application logs even if a future code change passes it through
  `log_with_context` by mistake.
- This service never attempts to solve CAPTCHAs, bypass authentication, use
  another person's session, spoof TLS/browser fingerprints, or circumvent
  LinkedIn's access controls - a challenge page is a terminal error, not a
  retry target. The mobile-User-Agent technique in section 5 is a request
  header, not a fingerprint spoof or an authentication bypass.
- CORS is configured via `CORS_ORIGINS` and should be locked down to the
  deployed frontend's origin in production instead of left at `*`.

## 18. Testing

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

62 tests cover: profile URL validation/normalization, embedded-JSON blob
extraction (the defensive fallback layer), every section parser (basic
profile, experience, education, skills, certifications, languages) against
sanitized fixture HTML modeled on the real mobile-rendered response,
malformed/truncated JSON handling, HTTP response classification
(404/401/403/429/authwall-redirect/challenge-page/redirect-loop) on the
fetcher, service-level fallback and error propagation, and the FastAPI
routes themselves (validation errors, error-code-to-status mapping, success
path). Fixtures under `backend/tests/fixtures/` are hand-built synthetic
HTML with fictional data - `profile_mobile_full.html` specifically mirrors
the real structural shape (class names, nesting, `data-delayed-url`/
`data-truncated-control` attributes) confirmed against a live authenticated
fetch, so tests run deterministically without any live network access or
LinkedIn credentials, while still pinning every parser against the markup
LinkedIn actually serves today.

Frontend: `cd frontend && npm run build` type-checks the whole app (no
separate test suite was added, per the challenge's "don't spend excessive
time on visual design" guidance - the priority was the API).
