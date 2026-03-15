"""GitHub API client: get PR diff and submit review comments."""

from __future__ import annotations

import httpx

from app.models.review import ReviewComment


class GitHubClient:
    """GitHub API for PR files (diff) and creating review comments."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._token = token
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
        }

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> list[tuple[str, str]]:
        """
        Fetch PR files and return list of (path, patch) for each changed file.
        Uses the files API which includes 'patch' per file.
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        with httpx.Client(headers=self._headers, timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        out: list[tuple[str, str]] = []
        for item in data:
            path = item.get("filename", "")
            patch = item.get("patch") or ""
            if path:
                out.append((path, patch))
        return out

    def submit_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comments: list[ReviewComment],
        body: str = "",
    ) -> None:
        """
        Submit a review with inline comments.
        event: COMMENT for comment-only review.
        """
        if not comments:
            return
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        review_comments = [
            {
                "path": c.path,
                "line": c.line,
                "body": c.body,
                **({"start_line": c.start_line} if c.start_line is not None else {}),
            }
            for c in comments
        ]
        payload = {
            "event": "COMMENT",
            "body": body or "Code review (automated).",
            "comments": review_comments,
        }
        with httpx.Client(headers=self._headers, timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
