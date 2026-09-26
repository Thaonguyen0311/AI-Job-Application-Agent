"""Job ingestion, shared by the jobs router and the autopilot service."""
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Job
from ..scraper.playwright_scraper import fetch_jobs


def ingest(db: Session, query: str | None = None) -> int:
    """Pull jobs from the configured source and upsert by external_id."""
    added = 0
    for j in fetch_jobs(query):
        if db.query(Job).filter(Job.external_id == j["external_id"]).first():
            continue
        db.add(Job(
            external_id=j["external_id"], title=j["title"], company=j.get("company", ""),
            location=j.get("location", ""), country=j.get("country", ""),
            remote=j.get("remote", False), url=j.get("url", ""),
            description=j.get("description", ""), skills=j.get("skills", []),
            requires_cover_letter=j.get("requires_cover_letter", False),
            apply_type=j.get("apply_type", "form"),
            source=j.get("source", "seed"), posted_at=datetime.utcnow(),
        ))
        added += 1
    db.commit()
    return added
