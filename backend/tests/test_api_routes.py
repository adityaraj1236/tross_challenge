from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.linkedin.exceptions import LinkedInAuthError
from app.linkedin.schemas import ProfileData, ProfileResponse
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_profile_endpoint_rejects_invalid_url() -> None:
    response = client.post("/api/linkedin/profile", json={"url": "https://example.com/not-linkedin"})
    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["error_code"] == "INVALID_URL"


def test_profile_endpoint_requires_url_field() -> None:
    response = client.post("/api/linkedin/profile", json={})
    assert response.status_code == 422


def test_profile_endpoint_maps_linkedin_errors_to_http_status() -> None:
    with patch("app.api.routes.LinkedInProfileService") as mock_service_cls:
        instance = mock_service_cls.return_value
        instance.get_profile = AsyncMock(side_effect=LinkedInAuthError("session expired"))
        instance.aclose = AsyncMock()

        response = client.post(
            "/api/linkedin/profile", json={"url": "https://www.linkedin.com/in/jane-doe/"}
        )

    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "AUTH_REQUIRED"


def test_profile_endpoint_returns_data_on_success() -> None:
    fake_response = ProfileResponse(
        data=ProfileData(
            linkedin_url="https://www.linkedin.com/in/jane-doe/",
            public_id="jane-doe",
            name="Jane Doe",
        )
    )
    with patch("app.api.routes.LinkedInProfileService") as mock_service_cls:
        instance = mock_service_cls.return_value
        instance.get_profile = AsyncMock(return_value=fake_response)
        instance.aclose = AsyncMock()

        response = client.post(
            "/api/linkedin/profile", json={"url": "https://www.linkedin.com/in/jane-doe/"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Jane Doe"
