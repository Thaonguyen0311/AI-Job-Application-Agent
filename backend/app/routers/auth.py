"""Authentication: register, login, and security-question password reset.

No email verification anywhere, by design. Forgot-password works purely through
the security question set at registration.
"""
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import (create_access_token, hash_password, normalize_answer,
                    verify_password)
from ..database import get_db
from ..models import Profile, User
from ..schemas import (ForgotResetIn, ForgotStartIn, LoginIn, RegisterIn, Token)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_RESET_ATTEMPT_LIMIT = 5
_RESET_WINDOW_SECONDS = 15 * 60
_reset_attempts: dict[int, tuple[int, float]] = {}
_reset_attempts_lock = Lock()


def _reserve_reset_attempt(user_id: int) -> None:
    """Reserve a guess before checking the answer, including concurrent requests."""
    with _reset_attempts_lock:
        now = monotonic()
        expired = [key for key, (_, end) in _reset_attempts.items() if end <= now]
        for key in expired:
            del _reset_attempts[key]
        count, end = _reset_attempts.get(user_id, (0, now + _RESET_WINDOW_SECONDS))
        if count >= _RESET_ATTEMPT_LIMIT:
            raise HTTPException(
                429,
                "Too many password reset attempts. Try again later.",
                headers={"Retry-After": str(int(end - now) + 1)},
            )
        _reset_attempts[user_id] = (count + 1, end)


@router.post("/register", response_model=Token)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if len(data.username.strip()) < 3:
        raise HTTPException(400, "Username must be at least 3 characters.")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if not data.security_question.strip() or not data.security_answer.strip():
        raise HTTPException(400, "A security question and answer are required.")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(409, "That username is taken. Try another.")

    user = User(
        username=data.username.strip(),
        hashed_password=hash_password(data.password),
        security_question=data.security_question.strip(),
        security_answer_hash=hash_password(normalize_answer(data.security_answer)),
    )
    user.profile = Profile()  # empty profile to fill in later
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.username), username=user.username)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Wrong username or password.")
    return Token(access_token=create_access_token(user.username), username=user.username)


@router.post("/login-json", response_model=Token)
def login_json(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Wrong username or password.")
    return Token(access_token=create_access_token(user.username), username=user.username)


@router.post("/forgot/start")
def forgot_start(data: ForgotStartIn, db: Session = Depends(get_db)):
    """Return the user's security question so they can answer it."""
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(404, "No account with that username.")
    return {"username": user.username, "security_question": user.security_question}


@router.post("/forgot/reset", response_model=Token)
def forgot_reset(data: ForgotResetIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(404, "No account with that username.")
    _reserve_reset_attempt(user.id)
    if not verify_password(normalize_answer(data.security_answer), user.security_answer_hash):
        raise HTTPException(401, "That answer doesn't match. Try again.")
    if len(data.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters.")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return Token(access_token=create_access_token(user.username), username=user.username)
