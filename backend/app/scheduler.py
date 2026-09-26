"""
Daily automation scheduler (APScheduler).

Starts a background scheduler that fires once a day at the configured local time
and runs auto-apply for every user who has autopilot enabled. The trigger is a
standard cron schedule, so it keeps firing every day for as long as the app runs.

Configure via env / config.py:
  SCHEDULE_ENABLED, SCHEDULE_HOUR, SCHEDULE_MINUTE, SCHEDULE_TIMEZONE
"""
from __future__ import annotations

import logging
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .database import SessionLocal
from .services import apply_service

log = logging.getLogger("jobquest.scheduler")

_scheduler: BackgroundScheduler | None = None
JOB_ID = "daily_autopilot"


def _run_daily():
    """The function the scheduler calls every day."""
    log.info("=== Daily autopilot triggered at %s ===", datetime.utcnow().isoformat())
    db = SessionLocal()
    try:
        result = apply_service.run_all_scheduled(db)
        log.info("=== Daily autopilot finished: %s ===", result)
    except Exception as exc:  # keep the scheduler alive on failure
        log.exception("Daily autopilot crashed: %s", exc)
    finally:
        db.close()


def _tz():
    if ZoneInfo:
        try:
            return ZoneInfo(settings.schedule_timezone)
        except Exception:
            log.warning("Unknown timezone %s, using UTC", settings.schedule_timezone)
    return None  # APScheduler falls back to its default/UTC


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.schedule_enabled:
        log.info("Scheduler disabled (SCHEDULE_ENABLED=false).")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=_tz())
    trigger = CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute,
                          timezone=_tz())
    _scheduler.add_job(_run_daily, trigger, id=JOB_ID, replace_existing=True,
                       misfire_grace_time=3600, coalesce=True)
    _scheduler.start()
    nxt = _scheduler.get_job(JOB_ID).next_run_time
    log.info("Scheduler started — daily autopilot at %02d:%02d %s (next run: %s)",
             settings.schedule_hour, settings.schedule_minute,
             settings.schedule_timezone, nxt)
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def schedule_info() -> dict:
    job = _scheduler.get_job(JOB_ID) if _scheduler else None
    return {
        "enabled": settings.schedule_enabled,
        "time": f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d}",
        "timezone": settings.schedule_timezone,
        "running": bool(_scheduler and _scheduler.running),
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }
