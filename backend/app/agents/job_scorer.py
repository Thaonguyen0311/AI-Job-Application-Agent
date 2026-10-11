"""
Job <-> profile similarity scoring.

Blends three signals into a 0-100 score:
  1. Skill overlap (weighted by learned preference boosts)     -> 55%
  2. Text similarity between profile and job description        -> 25%
  3. Role/location/remote fit against stated preferences        -> 20%

Pure Python + stdlib so it always runs and is deterministic for tests.
"""
from __future__ import annotations

import math
import re
from collections import Counter

STOP = set("""a an the and or of to in for with on at by from as is are be this that
your you we our their they it its will can may should would could job role work team
""".split())


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]*", (text or "").lower())
            if t not in STOP and len(t) > 1]


def _norm_skill(s: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", "", (s or "").lower())


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def profile_skill_set(profile) -> set[str]:
    skills = set(_norm_skill(s) for s in (profile.skills or []))
    # Mine skills mentioned inside experience/project bullets too.
    for block in (profile.experience or []) + (profile.projects or []):
        for b in block.get("bullets", []) or []:
            for tok in _tokens(b):
                skills.add(_norm_skill(tok))
    return {s for s in skills if s}


def profile_text(profile) -> str:
    parts = [profile.summary or "", " ".join(profile.skills or []),
             " ".join(profile.hobbies or []), profile.degree or ""]
    for block in (profile.experience or []) + (profile.projects or []):
        parts.append(block.get("title", "") or block.get("name", ""))
        parts.extend(block.get("bullets", []) or [])
    return " ".join(parts)


def score_job(profile, job, boosts: dict[str, float] | None = None) -> dict:
    """Return {score, matched_skills, missing_skills}."""
    boosts = boosts or {}
    prof_skills = profile_skill_set(profile)
    job_skills_raw = job.skills or []
    job_skills = {_norm_skill(s): s for s in job_skills_raw if _norm_skill(s)}

    matched, missing = [], []
    boost_bonus = 0.0
    for norm, original in job_skills.items():
        if norm in prof_skills or any(norm in ps or ps in norm for ps in prof_skills):
            matched.append(original)
            boost_bonus += boosts.get(norm, 0.0)   # positive AND negative learned signal
        else:
            missing.append(original)

    skill_score = (len(matched) / len(job_skills)) if job_skills else 0.4
    # Learned preferences nudge the score up (things that worked) or down
    # (skills tied to past rejections/withdrawals), capped at +/-15%.
    adj = max(-0.15, min(0.15, boost_bonus * 0.05))
    skill_score = max(0.0, min(1.0, skill_score + adj))

    text_score = _cosine(Counter(_tokens(profile_text(profile))),
                         Counter(_tokens(job.description)))

    fit = 0.0
    roles = [r.lower() for r in (profile.preferred_roles or [])]
    if roles and any(r in job.title.lower() or job.title.lower() in r for r in roles):
        fit += 0.5
    locs = [l.lower() for l in (profile.preferred_locations or [])]
    if job.remote or (locs and any(l in (job.location or "").lower() for l in locs)):
        fit += 0.5
    if not roles and not locs:
        fit = 0.5  # neutral when nothing stated

    score = 100 * (0.55 * skill_score + 0.25 * text_score + 0.20 * fit)
    return {
        "score": round(min(100.0, max(0.0, score)), 1),
        "matched_skills": matched,
        "missing_skills": missing,
    }
