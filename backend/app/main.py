"""JobQuest API entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents.adk_agent import adk_available
from .config import settings
from .database import init_db
from .routers import applications, auth, autopilot, cv, dashboard, jobs, profile
from .scheduler import schedule_info, start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()      # start the daily automation
    yield
    stop_scheduler()


app = FastAPI(title="JobQuest API", version="1.1.0",
              description="AI job-application copilot for students.",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend served separately; tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, profile.router, cv.router, jobs.router,
          applications.router, autopilot.router, dashboard.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "ai_engine": "google-adk" if adk_available() else "local-fallback",
        "apply_mode": settings.apply_mode,
        "job_source": settings.job_source,
        "scheduler": schedule_info(),
    }
