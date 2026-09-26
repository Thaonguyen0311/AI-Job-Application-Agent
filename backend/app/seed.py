"""Seed the DB with jobs and an optional demo user. Run: python -m app.seed"""
from datetime import datetime

from .auth import hash_password, normalize_answer
from .database import SessionLocal, init_db
from .models import Job, Profile, User
from .scraper.seed_jobs import SEED_JOBS

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"


def seed_jobs(db):
    added = 0
    for j in SEED_JOBS:
        if db.query(Job).filter(Job.external_id == j["external_id"]).first():
            continue
        db.add(Job(external_id=j["external_id"], title=j["title"],
                   company=j["company"], location=j["location"], country=j.get("country", ""),
                   remote=j["remote"], url=j["url"], description=j["description"],
                   skills=j["skills"], requires_cover_letter=j["requires_cover_letter"],
                   apply_type=j.get("apply_type", "form"), source=j.get("source", "seed"),
                   posted_at=datetime.utcnow()))
        added += 1
    db.commit()
    return added


def seed_demo_user(db):
    if db.query(User).filter(User.username == DEMO_USERNAME).first():
        return False
    user = User(
        username=DEMO_USERNAME, hashed_password=hash_password(DEMO_PASSWORD),
        security_question="What is your favourite programming language?",
        security_answer_hash=hash_password(normalize_answer("python")),
    )
    user.profile = Profile(
        full_name="Alex Rivera", email="alex.rivera@campus.edu",
        phone="+1 555 0100", linkedin="alexrivera", github="alexrivera",
        location="Remote", university="State University",
        degree="BSc Computer Science", graduation_year="2026", gpa="3.7",
        summary="Third-year CS student who loves building web apps and shipping fast.",
        skills=["Python", "JavaScript", "React", "SQL", "Git", "FastAPI", "HTML", "CSS"],
        experience=[{
            "title": "Web Dev Volunteer", "org": "Campus Coding Club",
            "dates": "2024 - Present",
            "bullets": ["Built the club website with React and deployed on Vercel.",
                        "Mentored 10+ first-years in JavaScript basics."],
        }],
        projects=[{
            "name": "StudyBuddy", "dates": "2024",
            "bullets": ["A FastAPI + React app pairing students for study sessions.",
                        "Implemented auth, matching and a dashboard."],
        }],
        hobbies=["Chess", "Photography", "Hackathons"],
        languages=["English (fluent)", "Spanish (conversational)"],
        preferred_roles=["Frontend Developer Intern", "Full-Stack Developer"],
        preferred_locations=["Remote"],
        onboarded=True,
    )
    db.add(user)
    db.commit()
    return True


def main():
    init_db()
    db = SessionLocal()
    try:
        j = seed_jobs(db)
        u = seed_demo_user(db)
        print(f"Seeded {j} jobs. Demo user created: {u} "
              f"(login: {DEMO_USERNAME} / {DEMO_PASSWORD})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
