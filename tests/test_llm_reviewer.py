"""Tests for LLMReviewer JSON parsing logic."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_reviewer import LLMReviewer


@pytest.fixture
def reviewer():
    with patch("app.services.llm_reviewer.ChatAnthropic"):
        return LLMReviewer(api_key="test")


def test_parse_comments_valid_json(reviewer):
    text = '[{"path": "foo.py", "line": 5, "body": "Nice", "severity": "info"}]'
    comments = reviewer._parse_comments(text)
    assert len(comments) == 1
    assert comments[0].path == "foo.py"
    assert comments[0].line == 5
    assert comments[0].body == "Nice"


def test_parse_comments_wrapped_in_markdown_code_block(reviewer):
    text = '```json\n[{"path": "bar.py", "line": 10, "body": "Fix this"}]\n```'
    comments = reviewer._parse_comments(text)
    assert len(comments) == 1
    assert comments[0].path == "bar.py"
    assert comments[0].line == 10


def test_parse_comments_empty_array(reviewer):
    comments = reviewer._parse_comments("[]")
    assert comments == []


def test_parse_comments_invalid_json_returns_empty(reviewer):
    comments = reviewer._parse_comments("this is not json at all")
    assert comments == []


def test_parse_comments_malformed_json_returns_empty(reviewer):
    comments = reviewer._parse_comments("[{invalid json}]")
    assert comments == []


def test_parse_comments_missing_required_fields_skipped(reviewer):
    # Missing 'body'
    text = '[{"path": "foo.py", "line": 1}]'
    comments = reviewer._parse_comments(text)
    assert comments == []


def test_parse_comments_multiple_comments(reviewer):
    text = '[{"path": "a.py", "line": 1, "body": "A"}, {"path": "b.py", "line": 2, "body": "B"}]'
    comments = reviewer._parse_comments(text)
    assert len(comments) == 2
    assert comments[0].path == "a.py"
    assert comments[1].path == "b.py"


def test_parse_comments_invalid_severity_ignored(reviewer):
    text = '[{"path": "x.py", "line": 3, "body": "ok", "severity": "critical"}]'
    comments = reviewer._parse_comments(text)
    assert len(comments) == 1
    assert comments[0].severity is None


def test_parse_comments_with_start_line(reviewer):
    text = '[{"path": "x.py", "line": 10, "body": "ok", "start_line": 5}]'
    comments = reviewer._parse_comments(text)
    assert len(comments) == 1
    assert comments[0].start_line == 5


def test_review_returns_empty_for_blank_diff(reviewer):
    result = reviewer.review([("file.py", "")], pr_title="test")
    assert result.comments == []
