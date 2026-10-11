"""Job ingestion + scored matching against the current user's profile."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..agents.job_scorer import score_job
from ..agents.preference_learner import compute_boosts
from ..auth import get_current_user
from ..database import get_db
from ..models import Application, Job, User
from ..schemas import JobMatchOut, JobOut
from ..services.jobs_service import ingest as _ingest

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def _ensure_jobs(db: Session):
    if db.query(Job).count() == 0:
        _ingest(db)


@router.post("/refresh")
def refresh(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    added = _ingest(db)
    total = db.query(Job).count()
    return {"added": added, "total": total}


@router.get("/meta")
def meta(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sources, countries and counts by application method."""
    _ensure_jobs(db)
    jobs = db.query(Job).all()
    sources = {}
    for j in jobs:
        sources[j.source] = sources.get(j.source, 0) + 1
    countries = sorted({j.country for j in jobs if j.country})
    external = sum(1 for j in jobs if j.apply_type != "form")
    return {
        "sources": [{"name": k, "count": v} for k, v in sorted(sources.items())],
        "countries": countries,
        "total_count": len(jobs),
        "applyable_count": len(jobs) - external,
        "external_count": external,
    }


@router.get("/matches", response_model=list[JobMatchOut])
def matches(q: str | None = None, min_score: float = 0.0, country: str | None = None,
            source: str | None = None,
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_jobs(db)

    boosts = compute_boosts(db, user.id)
    applied_ids = {a.job_id for a in
                   db.query(Application).filter(Application.user_id == user.id).all()}

    # Return all posts; application eligibility is exposed via apply_type.
    query = db.query(Job)
    if country and country != "all":
        query = query.filter(Job.country == country)
    if source and source != "all":
        query = query.filter(Job.source == source)

    out = []
    for job in query.all():
        if q and q.lower() not in (job.title + job.company + " ".join(job.skills or [])).lower():
            continue
        res = score_job(user.profile, job, boosts)
        if res["score"] < min_score:
            continue
        data = JobOut.model_validate(job).model_dump()
        data["match_score"] = res["score"]
        data["matched_skills"] = res["matched_skills"]
        data["missing_skills"] = res["missing_skills"]
        data["already_applied"] = job.id in applied_ids
        out.append(data)
    out.sort(key=lambda d: d["match_score"], reverse=True)
    return out
