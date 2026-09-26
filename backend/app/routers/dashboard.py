"""Dashboard aggregates: counts, funnel, score distribution, learned prefs."""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..agents.preference_learner import top_preferences
from ..auth import get_current_user
from ..database import get_db
from ..models import Application, STATUSES, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    apps = db.query(Application).filter(Application.user_id == user.id).all()
    total = len(apps)

    by_status = Counter(a.status for a in apps)
    status_counts = {s: by_status.get(s, 0) for s in STATUSES}

    scores = [a.match_score for a in apps]
    avg_score = round(sum(scores) / total, 1) if total else 0.0

    # Similarity buckets for the distribution chart.
    buckets = {"0-40": 0, "40-60": 0, "60-75": 0, "75-90": 0, "90-100": 0}
    for s in scores:
        if s < 40: buckets["0-40"] += 1
        elif s < 60: buckets["40-60"] += 1
        elif s < 75: buckets["60-75"] += 1
        elif s < 90: buckets["75-90"] += 1
        else: buckets["90-100"] += 1

    interviews = by_status.get("interview", 0) + by_status.get("offer", 0)
    response_rate = round(100 * (total - by_status.get("applied", 0)) / total, 1) \
        if total else 0.0
    interview_rate = round(100 * interviews / total, 1) if total else 0.0

    recent = sorted(apps, key=lambda a: a.created_at or 0, reverse=True)[:5]
    recent_out = [{
        "id": a.id, "title": a.job.title, "company": a.job.company,
        "score": a.match_score, "status": a.status, "auto": a.auto_applied,
    } for a in recent]

    return {
        "total_applications": total,
        "auto_applied": sum(1 for a in apps if a.auto_applied),
        "avg_score": avg_score,
        "response_rate": response_rate,
        "interview_rate": interview_rate,
        "status_counts": status_counts,
        "score_buckets": buckets,
        "recent": recent_out,
        "learned": top_preferences(db, user.id),
    }
