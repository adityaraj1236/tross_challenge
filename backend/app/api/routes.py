from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import Settings, get_settings
from ..logging_config import get_logger, log_with_context
from ..linkedin.exceptions import LinkedInError
from ..linkedin.schemas import ErrorResponse, HealthResponse, ProfileRequest, ProfileResponse
from ..linkedin.service import LinkedInProfileService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse()


@router.post(
    "/api/linkedin/profile",
    response_model=ProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    tags=["linkedin"],
)
async def get_linkedin_profile(
    payload: ProfileRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ProfileResponse:
    log_with_context(
        logger, "INFO", "Incoming profile request",
        context={"url": payload.url, "client": request.client.host if request.client else None},
    )

    service = LinkedInProfileService(settings)
    try:
        return await service.get_profile(payload.url)
    except LinkedInError as exc:
        log_with_context(
            logger, "WARNING", "LinkedIn profile request failed",
            context={"url": payload.url, "error_code": exc.error_code, "error": str(exc)},
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail={"success": False, "error_code": exc.error_code, "message": str(exc)},
        ) from exc
    except Exception as exc:
        log_with_context(
            logger, "ERROR", "Unexpected error while fetching LinkedIn profile",
            context={"url": payload.url, "error": str(exc)},
        )
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error_code": "INTERNAL_ERROR", "message": "Unexpected server error."},
        ) from exc
    finally:
        await service.aclose()
