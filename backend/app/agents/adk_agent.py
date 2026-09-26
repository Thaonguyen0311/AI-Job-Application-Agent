"""
Google ADK integration layer.

The whole product is designed to run with OR without Google ADK / a Gemini key.
 - If ADK + a key are present, `llm_complete()` routes prompts through an ADK
   `LlmAgent`, giving you real generative CVs, cover letters and reasoning.
 - If not, every caller has a deterministic local fallback, so the system is
   fully functional and testable offline (CI, demos, air-gapped grading).

Nothing in here raises at import time.
"""
from __future__ import annotations

import asyncio
import logging

from ..config import settings

log = logging.getLogger("jobquest.adk")

_AGENT = None
_ADK_READY = False

# Try to wire up a real ADK agent. Any failure => stay in fallback mode.
try:
    if settings.google_api_key:
        import os
        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

        from google.adk.agents import LlmAgent          # type: ignore
        from google.adk.runners import InMemoryRunner    # type: ignore
        from google.genai import types                   # type: ignore

        _AGENT = LlmAgent(
            name="jobquest_writer",
            model=settings.gemini_model,
            instruction=(
                "You are JobQuest, a career copilot for university students. "
                "You write concise, ATS-friendly, achievement-oriented CV and "
                "cover-letter content. You never invent facts about the "
                "candidate. Return only the requested content, no preamble."
            ),
        )
        _runner = InMemoryRunner(agent=_AGENT, app_name="jobquest")
        _ADK_READY = True
        log.info("Google ADK agent ready (model=%s)", settings.gemini_model)
except Exception as exc:  # pragma: no cover - depends on optional deps
    log.warning("ADK unavailable, using local fallback generator: %s", exc)
    _ADK_READY = False


def adk_available() -> bool:
    return _ADK_READY


async def _run_adk(prompt: str) -> str:  # pragma: no cover - needs live key
    from google.genai import types
    user_id, session_id = "jobquest_user", "jobquest_session"
    await _runner.session_service.create_session(
        app_name="jobquest", user_id=user_id, session_id=session_id
    )
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    chunks: list[str] = []
    async for event in _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    chunks.append(part.text)
    return "".join(chunks).strip()


def llm_complete(prompt: str) -> str | None:
    """Return generated text, or None if we should use the caller's fallback."""
    if not _ADK_READY:
        return None
    try:  # pragma: no cover - needs live key
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Rare: called from an async context. Use a fresh loop in a thread.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(_run_adk(prompt))).result()
        return asyncio.run(_run_adk(prompt))
    except Exception as exc:
        log.warning("ADK call failed, falling back: %s", exc)
        return None
