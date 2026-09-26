"""
Job ingestion.

Two modes (config.job_source):
  * "seed"  -> returns the built-in sample feed. Deterministic, offline, testable.
  * "live"  -> uses Playwright to scrape a real listings page. Requires the
               Playwright browser binaries (`playwright install chromium`) and
               network access. Kept generic; adapt selectors per target board.

Scraping third-party sites can violate their Terms of Service. Only enable
"live" against sources you are permitted to scrape.
"""
from __future__ import annotations

import logging

from ..config import settings
from .seed_jobs import SEED_JOBS

log = logging.getLogger("jobquest.scraper")


def fetch_jobs(query: str | None = None) -> list[dict]:
    if settings.job_source == "live":
        try:
            return _fetch_live(query)
        except Exception as exc:  # pragma: no cover - needs browser + network
            log.warning("Live scrape failed, using seed feed: %s", exc)
    return _filter(SEED_JOBS, query)


def _filter(jobs: list[dict], query: str | None) -> list[dict]:
    if not query:
        return list(jobs)
    q = query.lower()
    return [j for j in jobs
            if q in j["title"].lower()
            or q in j["company"].lower()
            or any(q in s.lower() for s in j.get("skills", []))]


def _fetch_live(query: str | None) -> list[dict]:  # pragma: no cover
    """Example Playwright scraper. Replace selectors for your target board."""
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        # Example only. Point this at a board you are allowed to scrape.
        url = f"https://example-jobs.invalid/search?q={query or 'intern'}"
        page.goto(url, timeout=30000)
        cards = page.query_selector_all(".job-card")
        for i, card in enumerate(cards):
            title = card.query_selector(".title")
            company = card.query_selector(".company")
            results.append({
                "external_id": f"live-{i}",
                "title": title.inner_text() if title else "Unknown",
                "company": company.inner_text() if company else "",
                "location": "", "remote": False,
                "url": url, "skills": [], "requires_cover_letter": False,
                "description": card.inner_text(),
            })
        browser.close()
    return results or _filter(SEED_JOBS, query)
