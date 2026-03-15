"""Tests for GitHub client (get PR diff and submit review)."""

import json

import pytest
import respx
from httpx import Response

from app.services.github_client import GitHubClient


@respx.mock
def test_get_pr_diff_returns_list_of_path_patch():
    respx.get("https://api.github.com/repos/owner/repo/pulls/1/files").mock(
        return_value=Response(
            200,
            json=[
                {"filename": "foo.py", "patch": "@@ -1 +1 @@\n+line"},
                {"filename": "bar.py", "patch": "@@ -0 +1 @@\n+bar"},
            ],
        )
    )
    client = GitHubClient(token="test_token")
    result = client.get_pr_diff("owner", "repo", 1)
    assert result == [
        ("foo.py", "@@ -1 +1 @@\n+line"),
        ("bar.py", "@@ -0 +1 @@\n+bar"),
    ]


@respx.mock
def test_get_pr_diff_skips_missing_patch():
    respx.get("https://api.github.com/repos/o/r/pulls/2/files").mock(
        return_value=Response(200, json=[{"filename": "binary.bin", "patch": None}])
    )
    client = GitHubClient(token="x")
    result = client.get_pr_diff("o", "r", 2)
    assert result == [("binary.bin", "")]


@respx.mock
def test_submit_review_posts_review_with_comments():
    respx.post("https://api.github.com/repos/a/b/pulls/3/reviews").mock(
        return_value=Response(201)
    )
    from app.models.review import ReviewComment

    client = GitHubClient(token="x")
    client.submit_review(
        "a",
        "b",
        3,
        [ReviewComment(path="f.py", line=10, body="comment")],
    )
    assert respx.calls.call_count == 1
    req = respx.calls.last.request
    assert req.method == "POST"
    body = json.loads(req.content)
    assert body["event"] == "COMMENT"
    assert len(body["comments"]) == 1
    assert body["comments"][0]["path"] == "f.py"
    assert body["comments"][0]["line"] == 10
    assert body["comments"][0]["body"] == "comment"
