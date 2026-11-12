"""Job ingestion from the seed fixture or Arbeitnow's public job API."""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import logging
import re

import httpx

from ..config import settings
from .seed_jobs import SEED_JOBS

log = logging.getLogger("jobquest.scraper")
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _TextOnly()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def fetch_jobs(query: str | None = None) -> list[dict]:
    if settings.job_source == "live":
        return _fetch_arbeitnow(query)
    return _filter(SEED_JOBS, query)


def _filter(jobs: list[dict], query: str | None) -> list[dict]:
    if not query:
        return list(jobs)
    q = query.lower()
    return [j for j in jobs
            if q in j["title"].lower()
            or q in j["company"].lower()
            or any(q in s.lower() for s in j.get("skills", []))]


def _fetch_arbeitnow(query: str | None) -> list[dict]:
    """Fetch current listings and mark external applications as manual-only."""
    response = httpx.get(ARBEITNOW_URL, params={"page": 1}, timeout=20.0,
                         headers={"User-Agent": "JobQuest/1.0 (job feed integration)"})
    response.raise_for_status()
    payload = response.json()
    jobs = payload.get("data", []) if isinstance(payload, dict) else []
    results = []
    for item in jobs:
        url = item.get("url", "")
        if not url.startswith(("https://", "http://")):
            continue
        title = item.get("title") or "Untitled role"
        company = item.get("company_name") or ""
        tags = item.get("tags") or []
        description = _plain_text(item.get("description") or "")
        searchable = " ".join((title, company, description, *tags))
        if query and query.casefold() not in searchable.casefold():
            continue
        created = item.get("created_at")
        posted = None
        if isinstance(created, (int, float)):
            posted = datetime.fromtimestamp(created, tz=timezone.utc).replace(tzinfo=None)
        location = item.get("location") or ""
        results.append({
            "external_id": f"arbeitnow-{item.get('slug') or url}",
            "title": title,
            "company": company,
            "location": location,
            "country": location.rsplit(",", 1)[-1].strip() if "," in location else location,
            "remote": bool(item.get("remote", False)),
            "url": url,
            "description": description,
            "skills": tags,
            "requires_cover_letter": False,
            # Arbeitnow links to external ATS application pages. We cannot
            # verify a direct, authenticated form, so never auto-submit these.
            "apply_type": "external",
            "source": "Arbeitnow",
            "posted_at": posted,
        })
    return results
