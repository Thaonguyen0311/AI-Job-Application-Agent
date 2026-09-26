"""
Preference learner.

Every time the user changes an application status we log a PreferenceSignal.
Positive outcomes (in_review / interview / offer) increase the weight of that
job's skills & attributes; negative outcomes (rejected / withdrawn) decrease it.
The resulting per-skill "boosts" feed back into the scorer so ranking adapts to
what actually works for this student.
"""
from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy.orm import Session

from ..models import PreferenceSignal, POSITIVE_STATUSES, NEGATIVE_STATUSES


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", "", (s or "").lower())


def outcome_for_status(status: str) -> tuple[str, float]:
    if status in POSITIVE_STATUSES:
        # Offers weigh most, interviews next.
        weight = {"in_review": 1.0, "interview": 2.0, "offer": 3.0}.get(status, 1.0)
        return "positive", weight
    if status in NEGATIVE_STATUSES:
        return "negative", 1.0
    return "neutral", 0.0


def record_signal(db: Session, user_id: int, job, status: str) -> None:
    outcome, weight = outcome_for_status(status)
    if outcome == "neutral":
        return
    features = {
        "skills": [_norm(s) for s in (job.skills or [])],
        "company": job.company,
        "remote": job.remote,
        "location": job.location,
    }
    db.add(PreferenceSignal(user_id=user_id, job_id=job.id, outcome=outcome,
                            weight=weight, features=features))
    db.commit()


def compute_boosts(db: Session, user_id: int) -> dict[str, float]:
    """Aggregate signals into per-skill boost values (can be negative)."""
    signals = db.query(PreferenceSignal).filter(
        PreferenceSignal.user_id == user_id).all()
    boosts: dict[str, float] = defaultdict(float)
    for sig in signals:
        sign = 1.0 if sig.outcome == "positive" else -1.0
        for skill in (sig.features or {}).get("skills", []):
            boosts[skill] += sign * sig.weight
    return dict(boosts)


def top_preferences(db: Session, user_id: int, k: int = 6) -> dict:
    """Human-readable summary for the dashboard 'what the system learned' card."""
    signals = db.query(PreferenceSignal).filter(
        PreferenceSignal.user_id == user_id).all()
    skill_score: dict[str, float] = defaultdict(float)
    company_score: dict[str, float] = defaultdict(float)
    remote_score = 0.0
    for sig in signals:
        sign = 1.0 if sig.outcome == "positive" else -1.0
        f = sig.features or {}
        for skill in f.get("skills", []):
            skill_score[skill] += sign * sig.weight
        if f.get("company"):
            company_score[f["company"]] += sign * sig.weight
        if f.get("remote"):
            remote_score += sign * sig.weight

    liked_skills = sorted([(s, v) for s, v in skill_score.items() if v > 0],
                          key=lambda x: -x[1])[:k]
    avoided_skills = sorted([(s, v) for s, v in skill_score.items() if v < 0],
                            key=lambda x: x[1])[:k]
    liked_companies = sorted([(c, v) for c, v in company_score.items() if v > 0],
                             key=lambda x: -x[1])[:k]
    rejections = sum(1 for s in signals if s.outcome == "negative")
    return {
        "liked_skills": [s for s, _ in liked_skills],
        "avoided_skills": [s for s, _ in avoided_skills],
        "liked_companies": [c for c, _ in liked_companies],
        "prefers_remote": remote_score > 0,
        "signal_count": len(signals),
        "rejection_count": rejections,
    }
