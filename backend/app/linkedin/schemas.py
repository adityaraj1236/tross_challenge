from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProfileRequest(BaseModel):
    url: str = Field(..., description="A LinkedIn profile URL, e.g. https://www.linkedin.com/in/jane-doe/")

    @field_validator("url")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("url must not be empty")
        return v.strip()


class DateInfo(BaseModel):
    month: Optional[int] = None
    year: Optional[int] = None

    def __str__(self) -> str:  # convenient for building display strings
        if self.year and self.month:
            return f"{self.month:02d}/{self.year}"
        if self.year:
            return str(self.year)
        return ""


class ExperienceItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class EducationItem(BaseModel):
    institution: Optional[str] = None
    institution_linkedin_url: Optional[str] = None
    institution_logo_url: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class SkillItem(BaseModel):
    name: str
    endorsement_count: Optional[int] = None


class CertificationItem(BaseModel):
    name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None


class LanguageItem(BaseModel):
    name: str
    proficiency: Optional[str] = None


class HonorItem(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    description: Optional[str] = None


class ProjectItem(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class VolunteerItem(BaseModel):
    organization: Optional[str] = None
    role: Optional[str] = None
    cause: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class PublicationItem(BaseModel):
    title: Optional[str] = None
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class CourseItem(BaseModel):
    name: Optional[str] = None
    number: Optional[str] = None


class ProfileData(BaseModel):
    linkedin_url: str
    public_id: str

    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    about: Optional[str] = None
    open_to_work: bool = False
    follower_count: Optional[int] = None

    profile_image_url: Optional[str] = None
    cover_image_url: Optional[str] = None

    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)
    honors: list[HonorItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    volunteer_experience: list[VolunteerItem] = Field(default_factory=list)
    courses: list[CourseItem] = Field(default_factory=list)
    publications: list[PublicationItem] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    success: bool = True
    data: Optional[ProfileData] = None
    partial: bool = Field(
        default=False,
        description="True if some sections could not be reliably extracted (see `warnings`).",
    )
    warnings: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
