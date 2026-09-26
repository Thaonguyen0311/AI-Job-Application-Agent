"""Applications: manual apply, auto-apply, status updates (with learning)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.job_scorer import score_job
from ..agents.preference_learner import compute_boosts, record_signal
from ..auth import get_current_user
from ..database import get_db
from ..models import Application, Job, STATUSES, User
from ..schemas import ApplicationOut, ApplyIn, AutoApplyIn, StatusUpdateIn
from ..services import apply_service

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut)
def apply(data: ApplyIn, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    job = db.get(Job, data.job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.apply_type != "form":
        raise HTTPException(400, "This job requires logging into an employer portal, "
                                 "so it can't be submitted through JobQuest.")
    if db.query(Application).filter(Application.user_id == user.id,
                                    Application.job_id == job.id).first():
        raise HTTPException(409, "You already applied to this job.")
    return apply_service.build_application(
        db, user, job, generate_cover_letter=data.generate_cover_letter,
        cover_letter_override=data.cover_letter, template=data.template,
        run_type="single")


@router.post("/auto", response_model=list[ApplicationOut])
def auto_apply(data: AutoApplyIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """Score every un-applied (form) job and auto-apply to the best matches."""
    boosts = compute_boosts(db, user.id)
    applied_ids = {a.job_id for a in
                   db.query(Application).filter(Application.user_id == user.id).all()}
    wanted = apply_service.effective_countries(data.countries or [], user.profile)
    candidates = []
    for job in db.query(Job).filter(Job.apply_type == "form").all():
        if job.id in applied_ids:
            continue
        if not apply_service.job_in_countries(job, wanted):
            continue
        res = score_job(user.profile, job, boosts)
        if res["score"] >= data.min_score:
            candidates.append((res["score"], job))
    candidates.sort(key=lambda x: x[0], reverse=True)

    created = []
    for _, job in candidates[: data.limit]:
        created.append(apply_service.build_application(
            db, user, job, generate_cover_letter=None, run_type="manual", auto=True))
    return created


@router.get("", response_model=list[ApplicationOut])
def list_applications(user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return (db.query(Application).filter(Application.user_id == user.id)
              .order_by(Application.created_at.desc()).all())


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id,
                                       Application.user_id == user.id).first()
    if not app:
        raise HTTPException(404, "Application not found.")
    return app


@router.get("/{app_id}/documents")
def get_documents(app_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id,
                                       Application.user_id == user.id).first()
    if not app:
        raise HTTPException(404, "Application not found.")
    return {"cv_html": app.cv_html, "cover_letter": app.cover_letter}


@router.patch("/{app_id}/status", response_model=ApplicationOut)
def update_status(app_id: int, data: StatusUpdateIn,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.status not in STATUSES:
        raise HTTPException(400, f"Status must be one of {STATUSES}.")
    app = db.query(Application).filter(Application.id == app_id,
                                       Application.user_id == user.id).first()
    if not app:
        raise HTTPException(404, "Application not found.")
    app.status = data.status
    if data.notes:
        app.notes = data.notes
    db.commit()
    record_signal(db, user.id, app.job, data.status)  # feed the learner
    db.refresh(app)
    return app
