"""Profile CRUD — the source data the agent uses to build CVs & cover letters."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Profile, User
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _ensure_profile(db: Session, user: User) -> Profile:
    if not user.profile:
        user.profile = Profile()
        db.commit()
        db.refresh(user)
    return user.profile


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _ensure_profile(db, user)


@router.put("", response_model=ProfileOut)
def update_profile(data: ProfileIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    profile = _ensure_profile(db, user)
    payload = data.model_dump()
    onboarded = payload.pop("onboarded", None)
    for field, value in payload.items():
        setattr(profile, field, value)
    if onboarded is not None:
        profile.onboarded = onboarded
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/completeness")
def completeness(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Nudge students to fill the fields that most improve match quality."""
    p = _ensure_profile(db, user)
    checks = {
        "Name": bool(p.full_name), "Email": bool(p.email), "Phone": bool(p.phone),
        "University": bool(p.university), "Degree": bool(p.degree),
        "Skills": bool(p.skills), "Experience": bool(p.experience),
        "Projects": bool(p.projects), "Summary": bool(p.summary),
        "Preferred roles": bool(p.preferred_roles),
    }
    done = sum(1 for v in checks.values() if v)
    return {"percent": round(100 * done / len(checks)),
            "missing": [k for k, v in checks.items() if not v]}
