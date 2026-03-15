"""Orchestration: fetch diff, call LLM reviewer, map comments to GitHub, submit review."""

from __future__ import annotations

from app.models.review import ReviewComment
from app.services.github_client import GitHubClient
from app.services.llm_reviewer import LLMReviewer


class ReviewService:
    """Coordinates GitHub client and LLM reviewer to perform PR review and post comments."""

    def __init__(self, github_client: GitHubClient, llm_reviewer: LLMReviewer) -> None:
        self._github = github_client
        self._llm = llm_reviewer

    def review_pr(
        self,
        repo_full_name: str,
        pr_number: int,
        pr_title: str = "",
        pr_description: str | None = None,
    ) -> None:
        """
        Fetch PR diff, run LLM review, post inline comments to the PR.
        repo_full_name: e.g. "owner/repo".
        """
        owner, _, repo = repo_full_name.partition("/")
        if not owner or not repo:
            raise ValueError(f"Invalid repo full name: {repo_full_name}")
        diff_by_file = self._github.get_pr_diff(owner, repo, pr_number)
        if not diff_by_file:
            return
        result = self._llm.review(
            diff_by_file,
            pr_title=pr_title,
            pr_description=pr_description,
        )
        if not result.comments:
            return
        self._github.submit_review(owner, repo, pr_number, result.comments)
