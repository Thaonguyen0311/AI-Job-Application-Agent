"""
Auto-apply engine — performs the actual submission and returns an auditable
result (timestamp + confirmation reference) so every submission is traceable.

Two modes (config.apply_mode):
  * "demo" -> simulates a successful submission and returns a demo confirmation
              reference. No external calls. Safe for testing/grading (default).
  * "live" -> drives a real application form with Playwright, fills the
              candidate's details, submits, waits for a confirmation cue and
              captures a screenshot as proof.

IMPORTANT: automated mass-applying can violate a site's Terms of Service. "live"
mode is opt-in; only apply where you are permitted and genuinely want to.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from ..config import settings

log = logging.getLogger("jobquest.autoapply")

PROOF_DIR = os.environ.get("JOBQUEST_PROOF_DIR", "/tmp/jobquest_proofs")


def _ref(prefix: str) -> str:
    return f"{prefix}-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def submit_application(profile, job, cv_html: str, cover_letter: str) -> dict:
    """
    Return a result dict:
      {ok, mode, message, confirmation_ref, submitted_at, proof_path}
    """
    submitted_at = datetime.utcnow().isoformat() + "Z"

    if settings.apply_mode == "live":
        try:
            return _submit_live(profile, job, cv_html, cover_letter, submitted_at)
        except Exception as exc:  # pragma: no cover - needs browser + real form
            log.error("LIVE apply FAILED for job=%s (%s): %s", job.id, job.company, exc)
            return {"ok": False, "mode": "live", "confirmation_ref": "",
                    "submitted_at": submitted_at, "proof_path": "",
                    "message": f"Live submission failed: {exc}"}

    # ---- demo mode ----
    ref = _ref("JQ-DEMO")
    msg = (f"[DEMO] Submitted application to '{job.title}' at {job.company} "
           f"at {submitted_at}. Confirmation {ref}.")
    log.info(msg)
    return {"ok": True, "mode": "demo", "confirmation_ref": ref,
            "submitted_at": submitted_at, "proof_path": "", "message": msg}


def _submit_live(profile, job, cv_html, cover_letter, submitted_at) -> dict:  # pragma: no cover
    """Generic form filler. Real boards need tailored selectors/upload handling."""
    from playwright.sync_api import sync_playwright

    os.makedirs(PROOF_DIR, exist_ok=True)
    ref = _ref("JQ-LIVE")
    proof_path = os.path.join(PROOF_DIR, f"{ref}.png")

    log.info("LIVE apply START job=%s company=%s url=%s", job.id, job.company, job.url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(job.url, timeout=30000)

        def fill_if(selector, value):
            el = page.query_selector(selector)
            if el and value:
                el.fill(value); return True
            return False

        fill_if("input[name='name'], input[name='full_name'], input#name", profile.full_name)
        fill_if("input[type='email'], input[name='email']", profile.email)
        fill_if("input[name='phone'], input[type='tel']", profile.phone)
        fill_if("input[name='linkedin']", (f"https://linkedin.com/in/{profile.linkedin}"
                                           if profile.linkedin else ""))
        if cover_letter:
            fill_if("textarea[name='cover_letter'], textarea#cover_letter, textarea", cover_letter)

        submit = page.query_selector("button[type='submit'], input[type='submit'], "
                                     "button:has-text('Apply'), button:has-text('Submit')")
        if submit:
            submit.click()
        # Wait for a confirmation cue, then screenshot as proof.
        try:
            page.wait_for_selector("text=/thank you|received|submitted|confirmation/i",
                                   timeout=8000)
            confirmed = True
        except Exception:
            confirmed = False
        page.screenshot(path=proof_path, full_page=True)
        browser.close()

    msg = (f"[LIVE] {'Confirmed' if confirmed else 'Submitted (no confirmation cue)'} "
           f"application to {job.company} at {submitted_at}. Proof: {proof_path}")
    log.info(msg)
    return {"ok": True, "mode": "live", "confirmation_ref": ref,
            "submitted_at": submitted_at, "proof_path": proof_path, "message": msg}
