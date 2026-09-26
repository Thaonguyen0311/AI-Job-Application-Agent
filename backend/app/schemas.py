"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ---------- Auth ----------
class RegisterIn(BaseModel):
    username: str
    password: str
    security_question: str
    security_answer: str


class LoginIn(BaseModel):
    username: str
    password: str


class ForgotStartIn(BaseModel):
    username: str


class ForgotResetIn(BaseModel):
    username: str
    security_answer: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# ---------- Profile ----------
class ProfileIn(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    location: str = ""
    university: str = ""
    degree: str = ""
    graduation_year: str = ""
    gpa: str = ""
    summary: str = ""
    skills: list[str] = []
    experience: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    hobbies: list[str] = []
    languages: list[str] = []
    preferred_roles: list[str] = []
    preferred_locations: list[str] = []
    onboarded: Optional[bool] = None


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    onboarded: bool = False
    updated_at: Optional[datetime] = None


# ---------- Jobs ----------
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    company: str
    location: str
    country: str
    remote: bool
    url: str
    description: str
    skills: list[str]
    requires_cover_letter: bool
    apply_type: str
    source: str
    posted_at: Optional[datetime] = None


class JobMatchOut(JobOut):
    match_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    already_applied: bool = False


# ---------- Applications ----------
class ApplyIn(BaseModel):
    job_id: int
    generate_cover_letter: Optional[bool] = None  # None = auto-decide by job
    cover_letter: Optional[str] = None  # user-edited cover letter (manual apply)
    template: str = "modern"            # chosen CV template


class AutoApplyIn(BaseModel):
    min_score: float = 60.0
    limit: int = 5
    countries: list[str] = []           # [] = any country


class StatusUpdateIn(BaseModel):
    status: str
    notes: str = ""


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    match_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    status: str
    auto_applied: bool
    notes: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    job: JobOut


class CVPreviewIn(BaseModel):
    job_id: Optional[int] = None
    template: str = "modern"


class CoverLetterIn(BaseModel):
    job_id: int


# ---------- Autopilot / scheduler ----------
class AutopilotIn(BaseModel):
    enabled: bool
    min_score: float = 60.0
    daily_limit: int = 5
    countries: list[str] = []


class AutopilotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    enabled: bool
    min_score: float
    daily_limit: int
    countries: list[str] = []
    last_run_at: Optional[datetime] = None
    last_run_count: int = 0


class SubmissionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_type: str
    status: str
    mode: str
    match_score: float
    confirmation_ref: str
    message: str
    created_at: Optional[datetime] = None
    job: Optional[JobOut] = None
