"""Tests for review service orchestration."""

from unittest.mock import MagicMock

import pytest

from app.models.review import ReviewComment, ReviewResult
from app.services.github_client import GitHubClient
from app.services.llm_reviewer import LLMReviewer
from app.services.review_service import ReviewService


def test_review_pr_calls_github_and_llm_and_submits():
    github = MagicMock(spec=GitHubClient)
    github.get_pr_diff.return_value = [("f.py", "@@ -0 +1 @@\n+code")]
    llm = MagicMock(spec=LLMReviewer)
    llm.review.return_value = ReviewResult(
        comments=[ReviewComment(path="f.py", line=1, body="nice")]
    )
    svc = ReviewService(github_client=github, llm_reviewer=llm)
    svc.review_pr("owner/repo", 1, pr_title="Fix bug")
    github.get_pr_diff.assert_called_once_with("owner", "repo", 1)
    llm.review.assert_called_once()
    call_args = llm.review.call_args
    assert call_args.args[0] == [("f.py", "@@ -0 +1 @@\n+code")]
    assert call_args.kwargs["pr_title"] == "Fix bug"
    github.submit_review.assert_called_once_with(
        "owner", "repo", 1, [ReviewComment(path="f.py", line=1, body="nice")]
    )


def test_review_pr_invalid_repo_raises():
    svc = ReviewService(github_client=MagicMock(), llm_reviewer=MagicMock())
    with pytest.raises(ValueError, match="Invalid repo"):
        svc.review_pr("invalid", 1)


def test_review_pr_no_diff_does_not_call_llm():
    github = MagicMock(spec=GitHubClient)
    github.get_pr_diff.return_value = []
    llm = MagicMock(spec=LLMReviewer)
    svc = ReviewService(github_client=github, llm_reviewer=llm)
    svc.review_pr("o/r", 1)
    llm.review.assert_not_called()
    github.submit_review.assert_not_called()


def test_review_pr_no_comments_does_not_submit():
    github = MagicMock(spec=GitHubClient)
    github.get_pr_diff.return_value = [("f.py", "patch")]
    llm = MagicMock(spec=LLMReviewer)
    llm.review.return_value = ReviewResult(comments=[])
    svc = ReviewService(github_client=github, llm_reviewer=llm)
    svc.review_pr("o/r", 1)
    github.submit_review.assert_not_called()
