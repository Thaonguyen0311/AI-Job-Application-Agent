"""CV preview (HTML) and export (PDF), tailored to an optional job."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..agents.cover_letter import render_cover_letter_text
from ..agents.cv_generator import render_cv, render_cv_pdf
from ..auth import get_current_user
from ..database import get_db
from ..models import Job, User
from ..schemas import CoverLetterIn, CVPreviewIn

router = APIRouter(prefix="/api/cv", tags=["cv"])


def _job(db, job_id):
    if not job_id:
        return None
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@router.get("/templates")
def templates():
    return {"templates": [
        {"id": "modern", "name": "Modern", "desc": "Violet accents, chips, clean grid."},
        {"id": "classic", "name": "Classic", "desc": "Serif, centered, timeless."},
    ]}


@router.post("/cover-letter/draft")
def cover_letter_draft(data: CoverLetterIn, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """A ready-to-edit cover letter draft for the review-and-apply flow."""
    job = db.get(Job, data.job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return {"cover_letter": render_cover_letter_text(user.profile, job),
            "required": job.requires_cover_letter}


@router.post("/preview")
def preview(data: CVPreviewIn, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    job = _job(db, data.job_id)
    html = render_cv(user.profile, job, data.template)
    return {"html": html}


@router.post("/pdf")
def pdf(data: CVPreviewIn, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)):
    job = _job(db, data.job_id)
    try:
        content = render_cv_pdf(user.profile, job, data.template)
    except Exception as exc:
        raise HTTPException(500, f"PDF engine unavailable: {exc}")
    fname = f"CV_{(user.profile.full_name or user.username).replace(' ', '_')}.pdf"
    return Response(content, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
