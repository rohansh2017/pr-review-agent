"""LangChain + Claude: structured prompt and parse review output to ReviewComment list."""

from __future__ import annotations

import json
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.review import ReviewComment, ReviewResult, Severity
from app.prompts.review_prompt import SYSTEM_PROMPT, build_user_prompt


class LLMReviewer:
    """Invoke Claude via LangChain and parse JSON array of comments."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._llm = ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            max_tokens=4096,
        )

    def review(
        self,
        diff_by_file: list[tuple[str, str]],
        pr_title: str = "",
        pr_description: str | None = None,
    ) -> ReviewResult:
        """
        Build combined diff, call Claude, parse response into ReviewResult.
        diff_by_file: list of (path, patch).
        """
        diff = "\n\n".join(
            f"--- File: {path}\n{patch}" for path, patch in diff_by_file if patch
        )
        if not diff.strip():
            return ReviewResult(comments=[])
        user_prompt = build_user_prompt(pr_title, pr_description, diff)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = self._llm.invoke(messages)
        text = response.content if hasattr(response, "content") else str(response)
        comments = self._parse_comments(text)
        return ReviewResult(comments=comments)

    def _parse_comments(self, text: str) -> list[ReviewComment]:
        """Extract JSON array from LLM response and map to ReviewComment list."""
        text = text.strip()
        # Try to find a JSON array in the response (in case of markdown code block)
        json_match = re.search(r"\[[\s\S]*\]", text)
        if not json_match:
            return []
        try:
            raw = json.loads(json_match.group())
        except json.JSONDecodeError:
            return []
        comments: list[ReviewComment] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            line = item.get("line")
            body = item.get("body")
            if path is None or line is None or body is None:
                continue
            try:
                line = int(line)
            except (TypeError, ValueError):
                continue
            severity = None
            if "severity" in item and item["severity"]:
                try:
                    severity = Severity(item["severity"])
                except ValueError:
                    pass
            start_line = item.get("start_line")
            if start_line is not None:
                try:
                    start_line = int(start_line)
                except (TypeError, ValueError):
                    start_line = None
            comments.append(
                ReviewComment(
                    path=str(path),
                    line=line,
                    body=str(body),
                    severity=severity,
                    start_line=start_line,
                )
            )
        return comments
