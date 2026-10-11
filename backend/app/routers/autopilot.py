"""Autopilot: daily auto-apply settings, on-demand run, and the audit log."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import SubmissionLog, User
from ..schemas import (ApplicationOut, AutopilotIn, AutopilotOut, SubmissionLogOut)
from ..scheduler import schedule_info
from ..services import apply_service

router = APIRouter(prefix="/api/autopilot", tags=["autopilot"])


@router.get("")
def get_autopilot(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = apply_service.get_or_create_settings(db, user.id)
    return {"settings": AutopilotOut.model_validate(s).model_dump(),
            "schedule": schedule_info()}


@router.put("", response_model=AutopilotOut)
def update_autopilot(data: AutopilotIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    s = apply_service.get_or_create_settings(db, user.id)
    s.enabled = data.enabled
    s.min_score = max(0.0, min(100.0, data.min_score))
    s.daily_limit = max(1, min(25, data.daily_limit))
    s.countries = data.countries or []
    db.commit(); db.refresh(s)
    return s


@router.post("/run-now", response_model=list[ApplicationOut])
def run_now(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run the daily automation immediately for this user (proof it works end-to-end)."""
    summary = apply_service.run_autopilot_for_user(db, user, run_type="manual")
    return summary.get("created", [])


@router.get("/logs", response_model=list[SubmissionLogOut])
def logs(limit: int = 50, user: User = Depends(get_current_user),
         db: Session = Depends(get_db)):
    return (db.query(SubmissionLog)
              .filter(SubmissionLog.user_id == user.id)
              .order_by(SubmissionLog.created_at.desc())
              .limit(limit).all())
