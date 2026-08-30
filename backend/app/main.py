from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .logging_config import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "LinkedIn Profile API starting up (environment=%s, linkedin_session_configured=%s)",
        settings.environment,
        settings.has_linkedin_session,
    )
    if not settings.has_linkedin_session:
        logger.warning(
            "No LINKEDIN_LI_AT cookie is configured - requests will be unauthenticated and "
            "LinkedIn will likely return an auth-wall for most profiles."
        )
    yield


app = FastAPI(
    title="LinkedIn Profile API",
    description=(
        "Accepts a LinkedIn profile URL and returns structured profile data. "
        "Fetches LinkedIn directly over HTTP - no browser is launched anywhere in this service."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
