"""End-to-end API tests. Run: pytest -q  (from backend/)"""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402

init_db()  # ensure tables exist for the test DB
client = TestClient(app)
AUTH = {}


def _token(username="tester", password="secret123"):
    r = client.post("/api/auth/register", json={
        "username": username, "password": password,
        "security_question": "pet name?", "security_answer": "Rex",
    })
    if r.status_code == 409:
        r = client.post("/api/auth/login-json",
                        json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def setup_module():
    AUTH["h"] = {"Authorization": f"Bearer {_token()}"}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_duplicate_rejected():
    r = client.post("/api/auth/register", json={
        "username": "tester", "password": "secret123",
        "security_question": "x", "security_answer": "y"})
    assert r.status_code == 409


def test_login_wrong_password():
    r = client.post("/api/auth/login-json",
                    json={"username": "tester", "password": "nope"})
    assert r.status_code == 401


def test_forgot_password_flow():
    client.post("/api/auth/register", json={
        "username": "forgetful", "password": "orig123",
        "security_question": "city?", "security_answer": "Paris"})
    start = client.post("/api/auth/forgot/start", json={"username": "forgetful"})
    assert start.status_code == 200
    assert "city" in start.json()["security_question"]
    # wrong answer
    bad = client.post("/api/auth/forgot/reset", json={
        "username": "forgetful", "security_answer": "London", "new_password": "new12345"})
    assert bad.status_code == 401
    # right answer (case-insensitive)
    good = client.post("/api/auth/forgot/reset", json={
        "username": "forgetful", "security_answer": "paris", "new_password": "new12345"})
    assert good.status_code == 200
    # can log in with new password
    login = client.post("/api/auth/login-json",
                        json={"username": "forgetful", "password": "new12345"})
    assert login.status_code == 200


def test_profile_update_and_completeness():
    payload = {
        "full_name": "Test User", "email": "t@e.com", "university": "MIT",
        "degree": "CS", "skills": ["Python", "React", "SQL"],
        "preferred_roles": ["Frontend Developer Intern"],
        "experience": [{"title": "Intern", "org": "Acme", "dates": "2024",
                        "bullets": ["Did React things"]}],
        "projects": [{"name": "Proj", "dates": "2023", "bullets": ["Built X"]}],
        "summary": "Keen student.",
    }
    r = client.put("/api/profile", json=payload, headers=AUTH["h"])
    assert r.status_code == 200
    assert r.json()["full_name"] == "Test User"
    c = client.get("/api/profile/completeness", headers=AUTH["h"])
    assert c.status_code == 200
    assert c.json()["percent"] > 50


def test_job_matches_scored_and_sorted():
    r = client.get("/api/jobs/matches", headers=AUTH["h"])
    assert r.status_code == 200
    jobs = r.json()
    assert len(jobs) >= 5
    scores = [j["match_score"] for j in jobs]
    assert scores == sorted(scores, reverse=True)
    # React profile should match the Frontend job well.
    top = jobs[0]
    assert top["match_score"] > 0
    assert "matched_skills" in top


def test_cv_preview_tailors_to_job():
    matches = client.get("/api/jobs/matches", headers=AUTH["h"]).json()
    job_id = matches[0]["id"]
    generic = client.post("/api/cv/preview", json={"template": "modern"},
                          headers=AUTH["h"]).json()["html"]
    tailored = client.post("/api/cv/preview",
                           json={"job_id": job_id, "template": "modern"},
                           headers=AUTH["h"]).json()["html"]
    assert "Test User" in generic
    assert isinstance(tailored, str) and len(tailored) > 200


def test_apply_and_status_update_learns():
    matches = client.get("/api/jobs/matches", headers=AUTH["h"]).json()
    job_id = matches[0]["id"]
    app_r = client.post("/api/applications", json={"job_id": job_id}, headers=AUTH["h"])
    assert app_r.status_code == 200
    app_id = app_r.json()["id"]
    # duplicate rejected
    dup = client.post("/api/applications", json={"job_id": job_id}, headers=AUTH["h"])
    assert dup.status_code == 409
    # update status -> interview (positive signal)
    upd = client.patch(f"/api/applications/{app_id}/status",
                       json={"status": "interview", "notes": "call scheduled"},
                       headers=AUTH["h"])
    assert upd.status_code == 200
    assert upd.json()["status"] == "interview"
    # dashboard reflects it and learning kicked in
    dash = client.get("/api/dashboard", headers=AUTH["h"]).json()
    assert dash["total_applications"] >= 1
    assert dash["interview_rate"] > 0
    assert dash["learned"]["signal_count"] >= 1


def test_auto_apply_creates_multiple():
    tok = _token("autopilot", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={
        "full_name": "Auto Pilot", "skills": ["Python", "SQL", "Docker", "React"],
        "preferred_roles": ["Backend"], "preferred_locations": ["Remote"]}, headers=h)
    r = client.post("/api/applications/auto", json={"min_score": 10, "limit": 3},
                    headers=h)
    assert r.status_code == 200
    created = r.json()
    assert 1 <= len(created) <= 3
    assert all(a["auto_applied"] for a in created)


def test_cover_letter_generated_when_required():
    tok = _token("coverme", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={
        "full_name": "Cover Me", "skills": ["Python", "SQL", "Pandas"]}, headers=h)
    matches = client.get("/api/jobs/matches", headers=h).json()
    cover_job = next(j for j in matches if j["requires_cover_letter"])
    r = client.post("/api/applications", json={"job_id": cover_job["id"]}, headers=h)
    assert r.status_code == 200
    docs = client.get(f"/api/applications/{r.json()['id']}/documents", headers=h).json()
    assert len(docs["cover_letter"]) > 50
    assert "Sincerely" in docs["cover_letter"]


def test_protected_route_requires_auth():
    r = client.get("/api/dashboard")
    assert r.status_code == 401


# ---------------- Automation: submission logs, autopilot, scheduler ----------------

def test_manual_apply_writes_submission_log():
    tok = _token("logger_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Log User",
               "skills": ["Python", "SQL", "Docker"]}, headers=h)
    matches = client.get("/api/jobs/matches", headers=h).json()
    r = client.post("/api/applications", json={"job_id": matches[0]["id"]}, headers=h)
    assert r.status_code == 200
    logs = client.get("/api/autopilot/logs", headers=h).json()
    assert len(logs) >= 1
    entry = logs[0]
    assert entry["status"] == "submitted"
    assert entry["confirmation_ref"].startswith("JQ-DEMO")  # traceable proof
    assert entry["mode"] == "demo"


def test_autopilot_settings_crud():
    tok = _token("pilot_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    got = client.get("/api/autopilot", headers=h).json()
    assert got["settings"]["enabled"] is False           # off by default
    assert "time" in got["schedule"] and "timezone" in got["schedule"]
    upd = client.put("/api/autopilot", json={"enabled": True, "min_score": 45, "daily_limit": 4}, headers=h)
    assert upd.status_code == 200
    body = upd.json()
    assert body["enabled"] is True and body["min_score"] == 45 and body["daily_limit"] == 4


def test_autopilot_run_now_applies_and_logs():
    tok = _token("runner_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Runner",
               "skills": ["Python", "SQL", "Docker", "React", "JavaScript"],
               "preferred_locations": ["Remote"]}, headers=h)
    client.put("/api/autopilot", json={"enabled": True, "min_score": 20, "daily_limit": 3}, headers=h)
    created = client.post("/api/autopilot/run-now", headers=h).json()
    assert 1 <= len(created) <= 3
    assert all(a["auto_applied"] for a in created)
    logs = client.get("/api/autopilot/logs", headers=h).json()
    scheduled_or_manual = [l for l in logs if l["run_type"] in ("manual", "scheduled")]
    assert len(scheduled_or_manual) >= 1
    # last_run tracking updated
    st = client.get("/api/autopilot", headers=h).json()["settings"]
    assert st["last_run_count"] >= 1 and st["last_run_at"]


def test_scheduler_run_all_applies_for_enabled_users_only():
    """Directly exercise the function the daily cron calls."""
    from app.database import SessionLocal
    from app.models import User, Profile, AutopilotSetting
    from app.services import apply_service
    db = SessionLocal()
    try:
        # make a fresh enabled user with a profile
        from app.auth import hash_password, normalize_answer
        u = User(username="cron_target", hashed_password=hash_password("secret123"),
                 security_question="q", security_answer_hash=hash_password(normalize_answer("a")))
        u.profile = Profile(full_name="Cron Target",
                            skills=["Python", "SQL", "Docker", "Linux"])
        db.add(u); db.commit(); db.refresh(u)
        s = apply_service.get_or_create_settings(db, u.id)
        s.enabled = True; s.min_score = 20; s.daily_limit = 5; db.commit()

        result = apply_service.run_all_scheduled(db)
        assert result["users"] >= 1
        assert result["applications"] >= 1
        # audit logs recorded as 'scheduled'
        from app.models import SubmissionLog
        sched_logs = db.query(SubmissionLog).filter(
            SubmissionLog.user_id == u.id, SubmissionLog.run_type == "scheduled").all()
        assert len(sched_logs) >= 1
    finally:
        db.close()


def test_health_reports_scheduler():
    h = client.get("/api/health").json()
    assert "scheduler" in h
    assert set(["enabled", "time", "timezone"]).issubset(h["scheduler"].keys())


# ---------------- New features: sources, filters, onboarding, manual apply ----------------

def test_jobs_meta_reports_sources_countries_and_hidden():
    tok = _token("meta_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Meta", "skills": ["Python"]}, headers=h)
    m = client.get("/api/jobs/meta", headers=h).json()
    source_names = [s["name"] for s in m["sources"]]
    assert "LinkedIn" in source_names                 # LinkedIn present
    assert m["hidden_login_required"] >= 1            # external jobs hidden
    assert len(m["countries"]) >= 3


def test_matches_only_returns_form_jobs():
    tok = _token("form_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Form", "skills": ["Python", "SQL"]}, headers=h)
    jobs = client.get("/api/jobs/matches", headers=h).json()
    assert len(jobs) >= 8
    assert all(j["apply_type"] == "form" for j in jobs)     # never a login-required job
    assert all("source" in j and "country" in j for j in jobs)


def test_country_filter():
    tok = _token("country_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Ctry", "skills": ["Python"]}, headers=h)
    ger = client.get("/api/jobs/matches?country=Germany", headers=h).json()
    assert len(ger) >= 1
    assert all(j["country"] == "Germany" for j in ger)


def test_cannot_apply_to_login_required_job():
    tok = _token("noext_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "NoExt", "skills": ["Python"]}, headers=h)
    # find an external job id directly from the DB
    from app.database import SessionLocal
    from app.models import Job
    db = SessionLocal()
    ext = db.query(Job).filter(Job.apply_type == "external").first()
    ext_id = ext.id if ext else None
    db.close()
    assert ext_id is not None
    r = client.post("/api/applications", json={"job_id": ext_id}, headers=h)
    assert r.status_code == 400  # refused — requires portal login


def test_manual_apply_with_edited_cover_letter():
    tok = _token("edit_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Edit User", "skills": ["Python", "SQL"]}, headers=h)
    jobs = client.get("/api/jobs/matches", headers=h).json()
    jid = jobs[0]["id"]
    custom = "This is my personally edited cover letter. Please hire me!"
    r = client.post("/api/applications",
                    json={"job_id": jid, "cover_letter": custom, "template": "classic"}, headers=h)
    assert r.status_code == 200
    docs = client.get(f"/api/applications/{r.json()['id']}/documents", headers=h).json()
    assert docs["cover_letter"] == custom          # user edit is what got saved/sent


def test_onboarding_flag_flow():
    tok = _token("onb_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    prof = client.get("/api/profile", headers=h).json()
    assert prof["onboarded"] is False               # new user not onboarded
    client.put("/api/profile", json={"full_name": "Onb", "skills": ["Python"], "onboarded": True}, headers=h)
    prof2 = client.get("/api/profile", headers=h).json()
    assert prof2["onboarded"] is True


def test_autopilot_country_scoped():
    tok = _token("apc_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "APC", "skills": ["Python", "SQL", "Pandas"]}, headers=h)
    client.put("/api/autopilot", json={"enabled": True, "min_score": 5, "daily_limit": 10,
                                       "countries": ["Germany"]}, headers=h)
    created = client.post("/api/autopilot/run-now", headers=h).json()
    assert len(created) >= 1
    assert all(a["job"]["country"] == "Germany" for a in created)  # respected country scope


def test_autoapply_defaults_to_preferred_countries():
    tok = _token("pref_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    # user prefers Germany only; do NOT pass countries to auto-apply
    client.put("/api/profile", json={"full_name": "Pref", "skills": ["Python", "SQL", "Pandas"],
                                     "preferred_locations": ["Germany"]}, headers=h)
    created = client.post("/api/applications/auto", json={"min_score": 5, "limit": 10}, headers=h).json()
    assert len(created) >= 1
    assert all(a["job"]["country"] == "Germany" for a in created)  # only preferred country


def test_country_alias_matching():
    from app.services.apply_service import job_in_countries
    class J:  # noqa
        country = "United States"; remote = False; location = "New York, USA"
    assert job_in_countries(J(), ["USA"]) is True      # alias resolves
    assert job_in_countries(J(), ["Germany"]) is False


def test_cover_letter_fits_one_page():
    from app.database import SessionLocal
    from app.models import User, Job
    from app.agents.cover_letter import _paragraphs
    tok = _token("cover_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Cover User", "degree": "BSc CS",
                                     "university": "State U", "skills": ["Python", "SQL", "React"]}, headers=h)
    client.get("/api/jobs/matches", headers=h)  # ensures jobs are seeded
    db = SessionLocal()
    u = db.query(User).filter(User.username == "cover_user").first()
    job = db.query(Job).filter(Job.apply_type == "form").first()
    paras = _paragraphs(u.profile, job)
    db.close()
    assert len(paras) <= 3
    assert sum(len(p.split()) for p in paras) <= 230   # one-page word budget


def test_languages_persist_and_appear_on_cv():
    tok = _token("lang_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Lang User", "skills": ["Python"],
                                     "languages": ["English (fluent)", "French (basic)"]}, headers=h)
    prof = client.get("/api/profile", headers=h).json()
    assert prof["languages"] == ["English (fluent)", "French (basic)"]
    prev = client.post("/api/cv/preview", json={"template": "classic"}, headers=h).json()["html"]
    assert "French (basic)" in prev and "LANGUAGES" in prev.upper()


def test_model_learns_from_rejections_lowers_score():
    """A rejection on a skill-heavy job should reduce that job's future score."""
    from app.database import SessionLocal
    from app.models import User, Job
    from app.agents.job_scorer import score_job
    from app.agents.preference_learner import compute_boosts, record_signal
    tok = _token("rej_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Rej", "skills": ["Python", "SQL", "Pandas"]}, headers=h)
    db = SessionLocal()
    u = db.query(User).filter(User.username == "rej_user").first()
    job = db.query(Job).filter(Job.apply_type == "form", Job.country == "Germany").first()
    before = score_job(u.profile, job, compute_boosts(db, u.id))["score"]
    # record several rejections tied to this job's skills
    for _ in range(3):
        record_signal(db, u.id, job, "rejected")
    after = score_job(u.profile, job, compute_boosts(db, u.id))["score"]
    db.close()
    assert after < before  # learned to down-rank rejected-skill jobs


def test_dashboard_reports_avoided_skills():
    tok = _token("avoid_user", "secret123")
    h = {"Authorization": f"Bearer {tok}"}
    client.put("/api/profile", json={"full_name": "Avoid", "skills": ["Python", "SQL"]}, headers=h)
    apps = client.post("/api/applications/auto", json={"min_score": 5, "limit": 2}, headers=h).json()
    if apps:
        client.patch(f"/api/applications/{apps[0]['id']}/status", json={"status": "rejected"}, headers=h)
    learned = client.get("/api/dashboard", headers=h).json()["learned"]
    assert "avoided_skills" in learned and "rejection_count" in learned
