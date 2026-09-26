"""Cover-letter generator (LLM via ADK, deterministic fallback otherwise)."""
from __future__ import annotations

import os
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .adk_agent import llm_complete
from .job_scorer import score_job

_TPL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_env = Environment(loader=FileSystemLoader(_TPL_DIR),
                   autoescape=select_autoescape(["html"]))


def _clip_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    clipped = " ".join(words[:max_words]).rstrip(",;:") 
    if not clipped.endswith((".", "!", "?")):
        clipped += "."
    return clipped


def _paragraphs(profile, job) -> list[str]:
    res = score_job(profile, job)
    matched = res["matched_skills"]

    prompt = (
        f"Write a concise 3-paragraph cover letter body (no greeting, no sign-off).\n"
        f"Hard limit: at most 3 short paragraphs and 220 words total so it fits on "
        f"one A4 page with the greeting and signature.\n"
        f"Candidate: {profile.full_name or 'a student'}, {profile.degree or ''} "
        f"at {profile.university or ''}. Skills: {', '.join(profile.skills or [])}.\n"
        f"Role: {job.title} at {job.company}. Job needs: {', '.join(job.skills or [])}.\n"
        f"Matched strengths to emphasise: {', '.join(matched) or 'general aptitude'}.\n"
        f"Keep it warm, specific, and honest. Separate paragraphs with a blank line."
    )
    generated = llm_complete(prompt)
    if generated:
        paras = [p.strip() for p in generated.split("\n\n") if p.strip()]
    else:
        # Deterministic fallback.
        strengths = ", ".join(matched[:3]) if matched else "quick learning and strong fundamentals"
        intro = (
            f"I am excited to apply for the {job.title} position at {job.company}. "
            f"As {('a ' + profile.degree) if profile.degree else 'a student'}"
            f"{(' at ' + profile.university) if profile.university else ''}, I am eager to "
            f"contribute and grow in a hands-on role."
        )
        body = (
            f"Your posting calls for {', '.join(job.skills[:4]) if job.skills else 'a range of skills'}, "
            f"which aligns well with my experience in {strengths}. "
        )
        if profile.projects:
            pr = profile.projects[0]
            body += f"For example, in my project {pr.get('name','')}, I applied these directly."
        close = (
            f"I would welcome the chance to bring my energy and skills to {job.company}. "
            f"Thank you for considering my application — I would love to discuss how I can help your team."
        )
        paras = [intro, body, close]

    # Enforce one-page limit: at most 3 paragraphs, ~220 words total.
    paras = paras[:3]
    budget = 220
    out = []
    for p in paras:
        if budget <= 0:
            break
        out.append(_clip_words(p, budget))
        budget -= len(p.split())
    return out


def render_cover_letter_html(profile, job) -> str:
    tpl = _env.get_template("cover_letter.html")
    return tpl.render(p=profile, job=job, today=date.today().strftime("%B %d, %Y"),
                      paragraphs=_paragraphs(profile, job))


def render_cover_letter_text(profile, job) -> str:
    paras = _paragraphs(profile, job)
    header = f"Dear Hiring Team at {job.company or 'your company'},\n\n"
    footer = f"\n\nSincerely,\n{profile.full_name or 'Your Name'}"
    return header + "\n\n".join(paras) + footer
