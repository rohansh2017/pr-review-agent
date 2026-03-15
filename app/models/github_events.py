"""Pydantic models for GitHub webhook payloads."""

from pydantic import BaseModel, Field


class RepositoryInfo(BaseModel):
    """Minimal repository info from webhook payload."""

    full_name: str = Field(..., description="e.g. owner/repo")
    default_branch: str | None = Field(None, alias="default_branch")


class PullRequestRef(BaseModel):
    """Minimal pull_request from webhook payload."""

    number: int
    title: str | None = None
    body: str | None = None
    draft: bool = False


class PullRequestEvent(BaseModel):
    """Payload for pull_request webhook events (opened, synchronize, etc.)."""

    action: str = Field(..., description="e.g. opened, synchronize")
    repository: RepositoryInfo
    pull_request: PullRequestRef = Field(..., alias="pull_request")

    model_config = {"populate_by_name": True}
