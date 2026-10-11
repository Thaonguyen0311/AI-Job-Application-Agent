"""
CV generator.

Produces an ATS-friendly CV, re-tailored for each specific job post so the
same profile yields a different, keyword-aligned CV per application.

Tailoring strategy:
  * Skills matching the job are promoted to the front (ATS keyword priority).
  * A job-aware professional summary is written (LLM via ADK, or a local
    template if no key is configured).
  * The chosen HTML template is rendered; the same HTML is used for on-screen
    preview and PDF export (WeasyPrint).
"""
from __future__ import annotations

import os
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .adk_agent import llm_complete
from .job_scorer import score_job

_TPL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_env = Environment(loader=FileSystemLoader(_TPL_DIR),
                   autoescape=select_autoescape(["html"]))

_TEMPLATES = {"modern": "cv_modern.html", "classic": "cv_classic.html"}

# Lightweight buckets so the CV shows categorised "Core skills" like a
# professional template, without needing the user to categorise them by hand.
_SKILL_CATEGORIES = [
    ("Languages & Frameworks", {
        "python", "javascript", "typescript", "java", "c", "c++", "c#", "go",
        "rust", "ruby", "php", "swift", "kotlin", "dart", "react", "vue",
        "angular", "node.js", "node", "django", "flask", "fastapi", "express",
        "spring", "next.js", "flutter", ".net", "rails", "svelte", "html", "css",
        "tailwind", "bootstrap", "pytorch", "tensorflow"}),
    ("Data & AI", {
        "sql", "postgresql", "mysql", "mongodb", "pandas", "numpy", "excel",
        "statistics", "machine learning", "deep learning", "nlp", "data analysis",
        "analytics", "power bi", "tableau", "spark", "hadoop", "r", "matlab",
        "scikit-learn", "llm", "rag"}),
    ("Cloud & DevOps", {
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "linux",
        "ci/cd", "jenkins", "git", "github", "gitlab", "bash", "nginx",
        "ansible", "cloud"}),
    ("Tools & Practices", {
        "figma", "jira", "agile", "scrum", "rest", "graphql", "testing",
        "playwright", "selenium", "pytest", "ui design", "prototyping",
        "user research", "seo", "marketing", "communication"}),
]


def _categorise_skills(skills: list[str]) -> list[dict]:
    """Group skills into labelled buckets; anything unknown goes to 'Additional'."""
    remaining = list(dict.fromkeys(skills))  # de-dupe, keep order
    groups = []
    for label, vocab in _SKILL_CATEGORIES:
        hit = [s for s in remaining if s.lower() in vocab]
        if hit:
            groups.append({"label": label, "skills": hit})
            remaining = [s for s in remaining if s not in hit]
    if remaining:
        groups.append({"label": "Additional", "skills": remaining})
    # If we somehow only produced one catch-all group, don't show a label.
    if len(groups) == 1 and groups[0]["label"] == "Additional":
        groups[0]["label"] = ""
    return groups


def _reorder_skills(profile, job) -> list[str]:
    if not job:
        return list(profile.skills or [])
    res = score_job(profile, job)
    matched = {m.lower() for m in res["matched_skills"]}
    skills = list(profile.skills or [])
    front = [s for s in skills if s.lower() in matched]
    back = [s for s in skills if s.lower() not in matched]
    # Add job-required skills the profile technically has via projects, etc.
    for extra in res["matched_skills"]:
        if extra not in front and extra not in back:
            front.append(extra)
    return front + back


def _tailored_summary(profile, job) -> str:
    base = profile.summary or ""
    if not job:
        return base
    prompt = (
        f"Write a 2-3 sentence professional summary for a CV.\n"
        f"Candidate: {profile.full_name or 'A student'}, "
        f"{profile.degree or ''} at {profile.university or ''}.\n"
        f"Their current summary: {base or 'N/A'}\n"
        f"Their skills: {', '.join(profile.skills or [])}\n"
        f"Target role: {job.title} at {job.company}.\n"
        f"Job needs: {', '.join(job.skills or [])}.\n"
        f"Emphasise the overlap. Do not invent experience. First person implied, "
        f"no 'I'. Return only the summary."
    )
    generated = llm_complete(prompt)
    if generated:
        return generated.strip()

    # Deterministic fallback tailoring.
    overlap = [s for s in (job.skills or [])
               if s.lower() in {x.lower() for x in (profile.skills or [])}]
    role = job.title
    bits = []
    who = profile.degree or "Student"
    where = f" at {profile.university}" if profile.university else ""
    bits.append(f"{who}{where} pursuing {role} opportunities.")
    if overlap:
        bits.append(f"Hands-on with {', '.join(overlap[:4])}.")
    elif profile.skills:
        bits.append(f"Skilled in {', '.join(list(profile.skills)[:4])}.")
    if base:
        bits.append(base)
    return " ".join(bits)


def render_cv(profile, job=None, template: str = "modern") -> str:
    tpl_name = _TEMPLATES.get(template, _TEMPLATES["modern"])
    tpl = _env.get_template(tpl_name)
    headline = job.title if job else " / ".join(profile.preferred_roles or [])
    ordered = _reorder_skills(profile, job)
    return tpl.render(
        p=profile,
        skills=ordered,
        skill_groups=_categorise_skills(ordered),
        summary=_tailored_summary(profile, job),
        headline=headline,
    )


def render_cv_pdf(profile, job=None, template: str = "modern") -> bytes:
    html = render_cv(profile, job, template)
    from weasyprint import HTML  # imported lazily; heavy dependency
    return HTML(string=html).write_pdf()
