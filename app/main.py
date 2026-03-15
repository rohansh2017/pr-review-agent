"""FastAPI app and webhook route registration."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from app.config import Settings, get_settings
from app.services.github_client import GitHubClient
from app.services.llm_reviewer import LLMReviewer
from app.services.review_service import ReviewService
from app.webhooks.github import handle_github_webhook


def get_github_client(settings: Settings = Depends(get_settings)) -> GitHubClient:
    return GitHubClient(token=settings.github_token)


def get_llm_reviewer(settings: Settings = Depends(get_settings)) -> LLMReviewer:
    return LLMReviewer(api_key=settings.anthropic_api_key)


def get_review_service(
    github_client: GitHubClient = Depends(get_github_client),
    llm_reviewer: LLMReviewer = Depends(get_llm_reviewer),
) -> ReviewService:
    return ReviewService(github_client=github_client, llm_reviewer=llm_reviewer)


_startup_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        settings = get_settings()
        _startup_logger.info(
            "PR Review Agent starting — github_token present: %s, anthropic_api_key present: %s, skip_draft_prs: %s",
            bool(settings.github_token),
            bool(settings.anthropic_api_key),
            settings.skip_draft_prs,
        )
    except Exception as exc:
        _startup_logger.error("Failed to load settings at startup: %s", exc)
        raise
    yield
    _startup_logger.info("PR Review Agent shut down.")


app = FastAPI(title="PR Review Agent", lifespan=lifespan)


@app.post("/webhooks/github")
async def webhook_github(
    request: Request,
    review_service: ReviewService = Depends(get_review_service),
    settings: Settings = Depends(get_settings),
):
    """GitHub webhook endpoint: receives pull_request events and runs review in background."""
    return await handle_github_webhook(
        request,
        review_service=review_service,
        webhook_secret=settings.webhook_secret,
        skip_draft_prs=settings.skip_draft_prs,
    )


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "github_token_set": bool(settings.github_token),
        "anthropic_key_set": bool(settings.anthropic_api_key),
        "skip_draft_prs": settings.skip_draft_prs,
    }
