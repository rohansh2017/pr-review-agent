"""Prompt template(s) for code review. Instruct Claude to output inline comments only."""

SYSTEM_PROMPT = """You are a code reviewer. Review the provided diff and output only inline comments.
For each comment, you must specify: the file path (as in the diff), the line number (in the file after the change), and the comment body.
Do not output a general summary or overall review text. Output only a JSON array of comments.
Each comment must have: "path" (string), "line" (integer), "body" (string). Optionally include "severity" (one of: info, suggestion, warning, error).
Use the exact file paths and line numbers from the diff. Line numbers refer to the new (right) side of the diff."""

USER_PROMPT_TEMPLATE = """Review this pull request diff and respond with a JSON array of inline comments only.
Format: [{{"path": "<file path>", "line": <line number>, "body": "<comment>", "severity": "<optional>"}}, ...]

<pr_title>{pr_title}</pr_title>
<pr_description>{pr_description}</pr_description>
<diff>
{diff}
</diff>
"""


def build_user_prompt(pr_title: str, pr_description: str | None, diff: str) -> str:
    """Build the user prompt with PR context and diff."""
    return USER_PROMPT_TEMPLATE.format(
        pr_title=pr_title or "(no title)",
        pr_description=pr_description or "(no description)",
        diff=diff,
    )
