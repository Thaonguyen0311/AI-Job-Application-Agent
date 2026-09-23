# JobQuest — an AI job-application copilot for students

Fill your profile once. JobQuest tailors a fresh, ATS-friendly CV for **every**
role, scores how well each job fits you, lets you **review & edit** before you
apply, and can **auto-apply every day** to the jobs that match your criteria —
tracking everything on a dashboard that **learns what's working for you**.

Built with **FastAPI + Google ADK + Playwright + APScheduler** on the backend and
a **vanilla-JS single-page app** on the front, wired together with **Docker
Compose**.

---

## Table of contents
1. [What it does](#what-it-does)
2. [Screens](#screens)
3. [Quick start with Docker](#quick-start-with-docker-recommended)
4. [Manual setup (no Docker)](#manual-setup-no-docker)
5. [First-run walkthrough](#first-run-walkthrough)
6. [How the key features work](#how-the-key-features-work)
7. [Configuration](#configuration-all-optional)
8. [API reference](#api-reference-all-under-api)
9. [Testing](#testing)
10. [Project structure](#project-structure)
11. [Troubleshooting](#troubleshooting)
12. [Notes, limits & ethics](#notes-limits--ethics)

---

## What it does

1. **Accounts** — username + password only, **no email verification**. Forgot
   your password? Answer the **security question** you set at sign-up.
2. **First-login onboarding** — before the dashboard, a short 3-step wizard
   collects the info needed to build CVs and match jobs (contact, education,
   skills, **languages**, preferred roles/countries, one experience).
3. **Guided product tour** — right after onboarding a 10-step interactive
   walkthrough highlights each part of the app (dashboard, job filters, review &
   apply, auto-apply, applications, autopilot, profile) with Next / Back / Skip.
   Replay anytime from **💡 Take a tour** in the sidebar.
4. **Job feed with clear sources** — every job shows where it came from
   (**LinkedIn**, Indeed, company career pages), its **country**, and whether it
   needs a cover letter.
5. **Only applyable jobs are shown** — jobs that require logging into an
   employer portal (e.g. Workday/Greenhouse accounts) are **hidden and never
   applied to**; the UI tells you how many were hidden and why. Only jobs with a
   direct form submission are surfaced.
6. **Filter jobs** — by search text, **country**, source, and minimum match score.
7. **Tailored CVs** — the same profile produces a *different* CV per job (matched
   skills first for ATS, summary rewritten around the role). Two professional
   templates (Modern, Classic) with a clean, recruiter-friendly layout:
   centred header, categorised **Core Skills**, Experience, Education, Projects &
   Achievements, and **Languages**. Export to PDF.
8. **Review & apply (manual)** — when you apply yourself, you first see the
   **prepared CV** (switch template) and an **editable cover letter** you can
   adjust before submitting. Generated cover letters are always kept to **one A4
   page**.
9. **Applies only to your preferred countries** — auto-apply and daily autopilot
   default to the countries in your profile (you can still override per run), so
   JobQuest never applies somewhere you don't want to work.
10. **Auto-apply (on demand)** — pick a minimum match score and **countries**, and
    JobQuest applies to the best matches, writing cover letters where required.
11. **Daily autopilot (scheduler)** — turn autopilot on and JobQuest runs
    auto-apply **once a day at a configured time**, scoped to your chosen
    **similarity rate and countries**, with a daily cap. Powered by APScheduler.
12. **Auditable submissions** — every submission (manual, auto, or scheduled)
    writes a log row with a **confirmation reference**
    (e.g. `JQ-DEMO-20260922-70FB6A0F`), status, mode and timestamp. Confirmation
    refs also appear next to each application.
13. **Application tracking + learning** — dashboard with totals, funnel,
    match-score distribution and rates. You set each status (interview,
    rejected, offer…) and JobQuest learns from it: skills tied to good outcomes
    are boosted, and **skills tied to rejections are down-ranked** in future
    scoring (shown on the dashboard as "Down-ranked after rejections").

---

## Screens

See the [`screenshots/`](screenshots) folder for the full A-to-Z flow:
onboarding → guided tour → job sources → country filter → review & apply →
**job submitted (with confirmation ref)** → auto-apply → applications →
**status switch (interview / rejected)** → dashboard (incl. rejection learning) →
autopilot, plus both CV templates rendered from the redesigned layout.

---

## Quick start with Docker (recommended)

**Prerequisite:** Docker Desktop (or Docker Engine + the Compose plugin).
Nothing else — no Python or Node needed on your machine.

```bash
cd jobquest
docker compose up --build
```

Wait for `jobquest-backend` to log `Application startup complete` and
`jobquest-frontend` to start, then open:

**http://localhost:8080**

- The frontend (nginx) serves the app and proxies `/api/*` to the backend.
- On first boot the backend seeds sample jobs and a **demo account**:
  - username **`demo`** / password **`demo123`**
  - security answer (for password reset): **`python`**
- Data persists in the `jobquest-data` Docker volume (SQLite).

To stop: `Ctrl-C`, then `docker compose down` (add `-v` to also wipe the data
volume).

---

## Manual setup (no Docker)

**Prerequisites**
- Python **3.11+**
- Node is **not required** (frontend is static). Any static file server works.
- WeasyPrint (PDF export) needs a few system libraries:
  - **Ubuntu/Debian:**
    `sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info`
  - **macOS (Homebrew):** `brew install pango cairo gdk-pixbuf libffi`
  - If you don't need PDF export, you can skip these — everything else still runs.

**1) Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # google-adk & playwright are optional (see below)
python -m app.seed               # seed sample jobs + demo user
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

> If `pip install -r requirements.txt` fails on the optional packages
> (`google-adk`, `playwright`), install the core set instead — the app runs fully
> without them:
> ```bash
> pip install fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings \
>   "python-jose[cryptography]" "passlib[bcrypt]" bcrypt python-multipart \
>   jinja2 weasyprint httpx apscheduler
> ```

**2) Frontend**

```bash
cd frontend
python -m http.server 5500
```

Open **http://localhost:5500**. When served this way (not behind the nginx
proxy) the app automatically talks to `http://localhost:8000/api`. To point it
elsewhere, run in the browser console:
`localStorage.setItem('jq_api','http://HOST:PORT/api')`.

---

## First-run walkthrough

1. Open the app → **Create an account** (username + password + a security
   question). No email needed.
2. Complete the **3-step onboarding**: about you → education, skills &
   languages → preferred roles/countries (+ one experience). Click **Finish**.
3. A **guided tour** starts automatically and walks you through every screen and
   button in 10 short steps. Skip it anytime, or replay later via **💡 Take a
   tour** in the sidebar.
4. On the **Find jobs** page, note the source badges (LinkedIn/Indeed/Company
   site), each job's country, and the line telling you how many login-required
   jobs were hidden. Filter by **country / source / match score**.
5. Click **Review & apply** on a job → check the tailored CV (switch
   Modern/Classic), **edit the cover letter** (always one page), then **Submit**.
   The card flips to *Applied* and the application gets a confirmation reference.
6. Or click **Auto-apply** — your **preferred countries are pre-selected** — pick
   a minimum score and let it apply to the best matches at once.
7. Go to **Autopilot**, turn it **on**, set the **similarity rate**, **countries**
   and daily cap, and **Save**. It runs every day at the configured time; hit
   **Run now** to prove it end-to-end.
8. In **Applications**, each row shows its confirmation reference. Change a status
   to *Interview* or *Rejected* — the dashboard's "What JobQuest learned about
   you" updates, boosting winning skills and **down-ranking skills tied to
   rejections**.

---

## How the key features work

**Job sources & the "only form-submission" rule.** Each job carries a `source`
and an `apply_type`. `apply_type: "form"` means a direct application form —
JobQuest can submit it. `apply_type: "external"` means the employer requires a
portal login; those jobs are **excluded from the list and can't be applied to**
(the API returns `400` if you try). `GET /api/jobs/meta` reports the sources,
countries, and how many jobs were hidden.

**Tailored CVs.** `agents/cv_generator.py` reorders skills so job-matched ones
come first (ATS priority) and rewrites the summary around the target role, then
renders `templates/cv_modern.html` or `cv_classic.html`. The same HTML is used
for on-screen preview and the PDF (WeasyPrint).

**Scoring.** `agents/job_scorer.py` blends skill overlap (55%), text similarity
(25%) and role/location fit (20%) into a 0–100 score, nudged by learned
preferences.

**Learning (incl. from rejections).** Every status change writes a
`PreferenceSignal` (`agents/preference_learner.py`). Positive outcomes
(in-review/interview/offer) raise the weight of that job's skills; negative ones
(rejected/withdrawn) lower them. Those signed weights feed back into the scorer,
so jobs heavy in skills tied to your rejections are **down-ranked** over time.
The dashboard surfaces both the boosted and the down-ranked skills.

**One-page cover letters.** Generated letters are capped to at most three
paragraphs and ~220 words, and the print CSS is tuned so the PDF always fits a
single A4 page. You can still edit freely in the review dialog before submitting.

**Preferred-country applying.** Auto-apply and autopilot apply only within your
chosen countries. If you don't pick any for a run, JobQuest falls back to the
countries in your profile (alias-aware, so "USA" matches "United States"), so it
never applies somewhere you didn't ask for.

**Guided tour.** A lightweight coach-mark overlay (`startTour` in `app.js`) walks
new users through the UI; completion is remembered per-user in `localStorage`.

**Daily automation.** `scheduler.py` (APScheduler) fires a cron job at
`SCHEDULE_HOUR:SCHEDULE_MINUTE` in `SCHEDULE_TIMEZONE`. For each user with
autopilot enabled it refreshes jobs, filters to `form` jobs in the chosen
countries above the chosen score, applies up to the daily cap, and logs each
submission. `GET /api/health` shows the scheduler's next run time.

---

## Configuration (all optional)

Set via environment (see `backend/.env.example` and `docker-compose.yml`).

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | dev key | JWT signing secret — **set a long random value in prod** |
| `DATABASE_URL` | `sqlite:///./jobquest.db` | any SQLAlchemy URL (e.g. Postgres) |
| `GOOGLE_API_KEY` | *(empty)* | Gemini key to enable real AI generation via ADK |
| `GEMINI_MODEL` | `gemini-2.0-flash` | model used when a key is set |
| `APPLY_MODE` | `demo` | `demo` simulates submission; `live` uses Playwright |
| `JOB_SOURCE` | `seed` | `seed` sample feed; `live` uses the scraper |
| `SCHEDULE_ENABLED` | `true` | master switch for the daily scheduler |
| `SCHEDULE_HOUR` | `8` | hour (0–23) of the daily run |
| `SCHEDULE_MINUTE` | `0` | minute of the daily run |
| `SCHEDULE_TIMEZONE` | `UTC` | e.g. `America/New_York`, `Asia/Dhaka` |

**AI engine.** With no `GOOGLE_API_KEY`, CVs and cover letters use a deterministic
local generator (fully functional, offline). With a key, they route through a
Google ADK `LlmAgent`. `GET /api/health` reports which engine is active.

---

## API reference (all under `/api`)

| Method | Path | Purpose |
|---|---|---|
| GET  | `/health` | status, active AI engine, modes, scheduler next-run |
| POST | `/auth/register` | create account (username, password, security Q/A) |
| POST | `/auth/login-json` | log in, returns JWT |
| POST | `/auth/forgot/start` | fetch the account's security question |
| POST | `/auth/forgot/reset` | verify answer, set new password |
| GET/PUT | `/profile` | read / update profile (incl. `onboarded` flag) |
| GET  | `/profile/completeness` | percent complete + missing fields |
| GET  | `/cv/templates` | available CV templates |
| POST | `/cv/preview` | tailored CV as HTML (optional `job_id`, `template`) |
| POST | `/cv/pdf` | tailored CV as a downloadable PDF |
| POST | `/cv/cover-letter/draft` | editable cover-letter draft for a job |
| GET  | `/jobs/meta` | sources, countries, hidden (login-required) count |
| GET  | `/jobs/matches` | scored jobs (`q`, `min_score`, `country`, `source`) — form-only |
| POST | `/jobs/refresh` | pull new jobs from the source |
| POST | `/applications` | apply to one job (accepts edited `cover_letter`, `template`) |
| POST | `/applications/auto` | auto-apply to top matches (`min_score`, `limit`, `countries`) |
| GET  | `/applications` | your applications |
| GET  | `/applications/{id}/documents` | that application's CV + cover letter |
| PATCH| `/applications/{id}/status` | update status (feeds the learner) |
| GET/PUT | `/autopilot` | daily autopilot settings (`min_score`, `countries`, `daily_limit`) + schedule |
| POST | `/autopilot/run-now` | run the daily automation immediately |
| GET  | `/autopilot/logs` | auditable submission log with confirmation refs |
| GET  | `/dashboard` | aggregate stats + learned preferences |

Interactive docs: **http://localhost:8000/docs**.

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -q
```

**29 end-to-end tests** cover: auth + security-question reset, profile &
completeness, onboarding flag, **languages on the CV**, scored/sorted matching,
**form-only filtering**, **country filter**, **refusing login-required jobs**,
per-job CV tailoring, manual apply with an **edited cover letter**,
**one-page cover letters**, auto & scheduled apply, **auto-apply defaulting to
preferred countries**, **country alias matching**, cover-letter generation,
submission logging with confirmation references, autopilot settings (incl.
**country scoping**), the daily scheduler function, the learning loop
**including down-ranking after rejections**, the dashboard's avoided-skills
report, and auth protection.

The whole suite runs offline (no API keys, no browser) thanks to the fallbacks.

---

## Project structure

```
jobquest/
├── docker-compose.yml           # backend (FastAPI) + frontend (nginx)
├── README.md
├── screenshots/                 # full A-to-Z flow + CV template renders
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py              # app + routers + scheduler + /api/health
│   │   ├── config.py            # env-driven settings (incl. schedule time)
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── models.py            # User, Profile, Job, Application,
│   │   │                        #   PreferenceSignal, AutopilotSetting, SubmissionLog
│   │   ├── schemas.py           # Pydantic models
│   │   ├── auth.py              # bcrypt + JWT + current-user dep
│   │   ├── scheduler.py         # APScheduler daily automation
│   │   ├── seed.py              # sample jobs + demo user
│   │   ├── routers/             # auth, profile, cv, jobs, applications,
│   │   │                        #   autopilot, dashboard
│   │   ├── services/
│   │   │   ├── apply_service.py     # shared apply + autopilot + audit logging
│   │   │   └── jobs_service.py      # job ingestion
│   │   ├── agents/
│   │   │   ├── adk_agent.py         # Google ADK wrapper (+ local fallback)
│   │   │   ├── cv_generator.py      # per-job tailored CV
│   │   │   ├── cover_letter.py      # cover-letter writer
│   │   │   ├── job_scorer.py        # similarity scoring
│   │   │   └── preference_learner.py# learns from status changes
│   │   ├── scraper/
│   │   │   ├── playwright_scraper.py# seed feed | live Playwright scrape
│   │   │   ├── auto_apply.py        # demo submit | live Playwright form-fill
│   │   │   └── seed_jobs.py         # built-in sample feed (sources, countries)
│   │   └── templates/           # cv_modern.html, cv_classic.html, cover_letter.html
│   └── tests/test_api.py        # 23 end-to-end tests
└── frontend/
    ├── Dockerfile               # nginx serving the SPA + /api proxy
    ├── nginx.conf
    ├── index.html               # auth, onboarding, app shell, modals
    ├── css/style.css
    └── js/app.js
```

---

## Troubleshooting

- **Charts are blank / fonts look plain offline.** The dashboard loads Chart.js
  and Google Fonts from a CDN. With no internet the numbers and cards still
  render; only the two charts and custom fonts fall back. Everything else works.
- **PDF export returns a 500.** WeasyPrint's system libraries are missing —
  install them (see [Manual setup](#manual-setup-no-docker)). Docker already
  includes them.
- **`pip install` fails on `google-adk` or `playwright`.** They're optional.
  Install the core set (snippet above); the app runs with the local AI fallback
  and demo submission.
- **Frontend can't reach the API in manual mode.** Make sure the backend is on
  `http://localhost:8000`, or set
  `localStorage.setItem('jq_api','http://HOST:PORT/api')` in the browser console.
- **Port already in use.** Change the published ports in `docker-compose.yml`
  (`8080:80`, `8000:8000`) or the `--port` flags in manual mode.
- **Live scraping / auto-apply.** Set `JOB_SOURCE=live` / `APPLY_MODE=live` and
  install browsers with `playwright install chromium`. The selectors are generic
  examples you must adapt per target site.

---

## Notes, limits & ethics

- SQLite is fine for a single instance / coursework; point `DATABASE_URL` at
  Postgres for real multi-user deployments.
- There is intentionally **no email verification**; password reset is
  security-question based, so choose a question only you can answer.
- **Automated applying can violate a site's Terms of Service** and can annoy
  employers. The default `demo`/`seed` modes never touch third-party sites.
  JobQuest also refuses to auto-apply to jobs that require an employer-portal
  login. Only enable `live` where you are permitted and genuinely want to apply.
