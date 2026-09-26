"""
Apply service — the single place applications get created and submitted.

Both the manual "Apply" button, the on-demand "Auto-apply", and the daily
scheduler go through here, so every submission:
  * generates a tailored CV (and a cover letter when the job needs one),
  * calls the submission engine (demo or live),
  * writes an auditable SubmissionLog row with a confirmation reference.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ..agents.cover_letter import render_cover_letter_text
from ..agents.cv_generator import render_cv
from ..agents.job_scorer import score_job
from ..agents.preference_learner import compute_boosts
from ..models import Application, AutopilotSetting, Job, SubmissionLog, User
from ..scraper.auto_apply import submit_application
from . import jobs_service

log = logging.getLogger("jobquest.apply")

# Common aliases so a stated preference like "USA" matches a job country
# stored as "United States".
_COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "u.s.": "united states",
    "uk": "united kingdom", "u.k.": "united kingdom", "england": "united kingdom",
    "uae": "united arab emirates", "holland": "netherlands",
}


def _canon(s: str) -> str:
    s = (s or "").strip().lower()
    return _COUNTRY_ALIASES.get(s, s)


def job_in_countries(job, countries: list[str]) -> bool:
    """True if the job belongs to one of the wanted countries (alias + remote aware)."""
    if not countries:
        return True  # no restriction
    wanted = {_canon(c) for c in countries}
    jc = _canon(job.country)
    if jc in wanted:
        return True
    if (job.remote or jc == "remote") and "remote" in wanted:
        return True
    # last-resort: match against the free-text location
    loc = (job.location or "").lower()
    return any(w and w in loc for w in wanted)


def effective_countries(explicit: list[str] | None, profile) -> list[str]:
    """What countries to actually apply in.

    An explicit choice (from the auto-apply modal or autopilot settings) always
    wins. Otherwise we fall back to the user's *preferred* locations so we only
    ever apply to jobs in the countries the user actually wants.
    """
    if explicit:
        return explicit
    return list((profile.preferred_locations or []) if profile else [])


def get_or_create_settings(db: Session, user_id: int) -> AutopilotSetting:
    s = db.query(AutopilotSetting).filter(AutopilotSetting.user_id == user_id).first()
    if not s:
        s = AutopilotSetting(user_id=user_id)
        db.add(s); db.commit(); db.refresh(s)
    return s


def _log(db, user_id, job, application_id, run_type, status, result, score):
    entry = SubmissionLog(
        user_id=user_id, job_id=job.id if job else None, application_id=application_id,
        run_type=run_type, status=status, mode=(result or {}).get("mode", "demo"),
        match_score=score, confirmation_ref=(result or {}).get("confirmation_ref", ""),
        message=(result or {}).get("message", ""),
    )
    db.add(entry); db.commit()
    return entry


def build_application(db: Session, user: User, job: Job,
                     generate_cover_letter: bool | None = None,
                     cover_letter_override: str | None = None,
                     template: str = "modern",
                     run_type: str = "single", auto: bool = False) -> Application:
    """Create + submit one application, writing an audit log. Assumes no dup."""
    # Safety: never auto-submit to jobs that require an employer-portal login.
    if job.apply_type != "form":
        raise ValueError("This job requires logging into an employer portal; "
                         "JobQuest does not auto-apply to it.")

    res = score_job(user.profile, job, compute_boosts(db, user.id))
    cv_html = render_cv(user.profile, job, template=template)

    if cover_letter_override is not None:
        cover = cover_letter_override
    else:
        want_cover = job.requires_cover_letter if generate_cover_letter is None else generate_cover_letter
        cover = render_cover_letter_text(user.profile, job) if want_cover else ""

    result = submit_application(user.profile, job, cv_html, cover)

    app = Application(
        user_id=user.id, job_id=job.id, match_score=res["score"],
        matched_skills=res["matched_skills"], missing_skills=res["missing_skills"],
        status="applied", cv_html=cv_html, cover_letter=cover,
        auto_applied=auto, notes=result["message"],
    )
    db.add(app); db.commit(); db.refresh(app)

    _log(db, user.id, job, app.id, run_type,
         "submitted" if result.get("ok") else "failed", result, res["score"])
    return app


def run_autopilot_for_user(db: Session, user: User, run_type: str = "scheduled") -> dict:
    """
    Score every un-applied job and apply to the strongest matches, respecting the
    user's min_score and daily_limit. Returns a summary and updates last_run.
    """
    settings_row = get_or_create_settings(db, user.id)
    if not user.profile:
        return {"created": [], "considered": 0, "reason": "no profile"}

    jobs_service.ingest(db)  # make sure the feed is fresh
    boosts = compute_boosts(db, user.id)
    applied_ids = {a.job_id for a in
                   db.query(Application).filter(Application.user_id == user.id).all()}
    wanted = effective_countries(settings_row.countries or [], user.profile)

    candidates = []
    for job in db.query(Job).filter(Job.apply_type == "form").all():
        if job.id in applied_ids:
            continue
        if not job_in_countries(job, wanted):
            continue
        res = score_job(user.profile, job, boosts)
        if res["score"] >= settings_row.min_score:
            candidates.append((res["score"], job))
    candidates.sort(key=lambda x: x[0], reverse=True)

    created = []
    for _, job in candidates[: settings_row.daily_limit]:
        created.append(build_application(db, user, job, generate_cover_letter=None,
                                         run_type=run_type, auto=True))

    settings_row.last_run_at = datetime.utcnow()
    settings_row.last_run_count = len(created)
    db.commit()
    log.info("Autopilot(%s) user=%s applied=%d/%d candidates",
             run_type, user.username, len(created), len(candidates))
    return {"created": created, "considered": len(candidates)}


def run_all_scheduled(db: Session) -> dict:
    """Run the daily job for every user who has autopilot enabled."""
    enabled = db.query(AutopilotSetting).filter(AutopilotSetting.enabled == True).all()  # noqa: E712
    total = 0
    for s in enabled:
        user = db.get(User, s.user_id)
        if not user:
            continue
        summary = run_autopilot_for_user(db, user, run_type="scheduled")
        total += len(summary.get("created", []))
    log.info("Scheduled run complete: %d users, %d applications submitted", len(enabled), total)
    return {"users": len(enabled), "applications": total,
            "ran_at": datetime.utcnow().isoformat() + "Z"}
