"""Pydantic models for code review results (LLM output and GitHub API)."""

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Optional severity for a review comment."""

    info = "info"
    suggestion = "suggestion"
    warning = "warning"
    error = "error"


class ReviewComment(BaseModel):
    """A single inline review comment (file, line, body)."""

    path: str = Field(..., description="Repository-relative file path")
    line: int = Field(..., description="Line number in the file (after the change)")
    body: str = Field(..., description="Comment text")
    severity: Severity | None = Field(None, description="Optional severity")
    start_line: int | None = Field(None, description="For multi-line comments")


class ReviewResult(BaseModel):
    """Aggregate result of a code review (list of inline comments)."""

    comments: list[ReviewComment] = Field(default_factory=list)
