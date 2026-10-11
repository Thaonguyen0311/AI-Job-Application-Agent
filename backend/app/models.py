"""ORM models."""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Forgot-password: security question (no email verification anywhere).
    security_question = Column(String, nullable=False)
    security_answer_hash = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False,
                           cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user",
                                cascade="all, delete-orphan")
    preferences = relationship("PreferenceSignal", back_populates="user",
                               cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    full_name = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    linkedin = Column(String, default="")
    github = Column(String, default="")
    location = Column(String, default="")
    university = Column(String, default="")
    degree = Column(String, default="")
    graduation_year = Column(String, default="")
    gpa = Column(String, default="")

    summary = Column(Text, default="")
    # JSON blobs so students can add flexible rich content.
    skills = Column(JSON, default=list)          # ["Python", "React", ...]
    experience = Column(JSON, default=list)       # [{title, org, dates, bullets:[]}]
    projects = Column(JSON, default=list)         # [{name, dates, bullets:[]}]
    hobbies = Column(JSON, default=list)          # ["Chess", "Photography"]
    languages = Column(JSON, default=list)        # ["English (fluent)", ...]
    preferred_roles = Column(JSON, default=list)  # ["Frontend Intern", ...]
    preferred_locations = Column(JSON, default=list)

    onboarded = Column(Boolean, default=False)  # completed first-login setup

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)  # id from source (dedupe)
    title = Column(String, nullable=False)
    company = Column(String, default="")
    location = Column(String, default="")
    country = Column(String, default="", index=True)
    remote = Column(Boolean, default=False)
    url = Column(String, default="")
    description = Column(Text, default="")
    skills = Column(JSON, default=list)
    requires_cover_letter = Column(Boolean, default=False)
    apply_type = Column(String, default="form")  # form | external (login required)
    source = Column(String, default="seed")
    posted_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))

    match_score = Column(Float, default=0.0)         # 0-100 similarity
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)

    status = Column(String, default="applied")       # see STATUSES
    cv_html = Column(Text, default="")               # tailored CV snapshot
    cover_letter = Column(Text, default="")
    auto_applied = Column(Boolean, default=False)
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job")


class PreferenceSignal(Base):
    """Every status change becomes a learning signal for the preference model."""
    __tablename__ = "preference_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    outcome = Column(String)          # positive | negative | neutral
    weight = Column(Float, default=1.0)
    features = Column(JSON, default=dict)  # {skills, company, remote, ...}
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class AutopilotSetting(Base):
    """Per-user daily auto-apply configuration used by the scheduler."""
    __tablename__ = "autopilot_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    enabled = Column(Boolean, default=False)
    min_score = Column(Float, default=60.0)
    daily_limit = Column(Integer, default=5)
    countries = Column(JSON, default=list)   # [] = any country
    last_run_at = Column(DateTime, nullable=True)
    last_run_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class SubmissionLog(Base):
    """
    Auditable record of every submission attempt — this is the 'proof' that
    the automation ran and completed. One row per job the automation touched.
    """
    __tablename__ = "submission_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    run_type = Column(String, default="manual")   # scheduled | manual | single
    status = Column(String, default="submitted")  # submitted | duplicate | failed | skipped
    mode = Column(String, default="demo")         # demo | live
    match_score = Column(Float, default=0.0)
    confirmation_ref = Column(String, default="")
    message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job")


# Canonical status lifecycle used across the app.
STATUSES = [
    "applied", "in_review", "interview", "offer", "rejected", "withdrawn"
]
POSITIVE_STATUSES = {"in_review", "interview", "offer"}
NEGATIVE_STATUSES = {"rejected", "withdrawn"}
