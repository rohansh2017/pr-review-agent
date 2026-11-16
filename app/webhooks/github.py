"""GitHub webhook handler: verify signature, parse payload, dispatch to review service."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time

from fastapi import Request, Response

from app.models.github_events import PullRequestEvent
from app.services.review_service import ReviewService

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = [1, 2, 4]  # seconds between attempts

# Per-PR rate limiting: maps "owner/repo#pr_number" -> last review timestamp
_last_review_time: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 60


async def _run_review_background(
    review_service: ReviewService,
    repo_full_name: str,
    pr_number: int,
    pr_title: str,
    pr_description: str | None,
) -> None:
    """Run review in a thread with retries. Logs outcome; swallows final exception."""
    logger.info("Review started for %s PR #%s", repo_full_name, pr_number)
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            await asyncio.to_thread(
                review_service.review_pr,
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                pr_title=pr_title,
                pr_description=pr_description,
            )
            logger.info("Review completed for %s PR #%s", repo_full_name, pr_number)
            return
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF[attempt]
                logger.warning(
                    "Review attempt %d/%d failed for %s PR #%s, retrying in %ds: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    repo_full_name,
                    pr_number,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
    logger.exception(
        "Review failed for %s PR #%s after %d attempts: %s",
        repo_full_name,
        pr_number,
        _MAX_RETRIES,
        last_exc,
    )


def verify_signature(payload_body: bytes, signature: str | None, secret: str) -> bool:
    """Verify X-Hub-Signature-256 (HMAC SHA-256 of body with webhook secret)."""
    if not signature or not secret:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def handle_github_webhook(
    request: Request,
    review_service: ReviewService,
    webhook_secret: str,
    skip_draft_prs: bool = True,
) -> Response:
    """
    Handle POST /webhooks/github.
    Verify signature, parse pull_request event, schedule review in background, return 200.
    """
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(body, sig, webhook_secret):
        return Response(status_code=401, content="Invalid signature")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")
    event = request.headers.get("X-GitHub-Event", "")
    if event != "pull_request":
        return Response(status_code=200, content="ignored")
    action = data.get("action")
    if action not in ("opened", "synchronize"):
        return Response(status_code=200, content="ignored")
    try:
        payload = PullRequestEvent.model_validate(data)
    except Exception:
        return Response(status_code=400, content="Invalid payload")
    if skip_draft_prs and payload.pull_request.draft:
        logger.info("Skipping draft PR %s #%s", payload.repository.full_name, payload.pull_request.number)
        return Response(status_code=200, content="ignored")
    repo = payload.repository.full_name
    pr = payload.pull_request
    rate_key = f"{repo}#{pr.number}"
    now = time.monotonic()
    last = _last_review_time.get(rate_key)
    # monotonic() can be under 60 right after boot, so "never reviewed" must not default to 0
    if last is not None and now - last < _RATE_LIMIT_SECONDS:
        logger.info("Rate limited review for %s PR #%s", repo, pr.number)
        return Response(status_code=200, content="rate limited")
    _last_review_time[rate_key] = now
    asyncio.create_task(
        _run_review_background(
            review_service,
            repo,
            pr.number,
            pr.title or "",
            pr.body,
        )
    )
    return Response(status_code=200, content="ok")
