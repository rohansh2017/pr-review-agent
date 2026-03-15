# PR Review Agent

An autonomous code review bot powered by Claude. When a pull request is opened or updated, it fetches the diff via the GitHub API, runs it through Claude for analysis, and posts inline review comments directly on the PR.

## How it works

1. GitHub sends a `pull_request` webhook event (`opened` or `synchronize`)
2. The agent verifies the HMAC-SHA256 signature and returns `200` immediately
3. A background task fetches the PR diff and sends it to Claude
4. Claude returns structured JSON comments; the agent posts them as inline PR review comments

## Stack

- **FastAPI** — async webhook server
- **LangChain + Anthropic** — Claude integration with structured JSON output
- **httpx** — GitHub API calls
- **Pydantic** — settings and payload validation

## Setup

### Prerequisites

- Python 3.10+
- A GitHub Personal Access Token with `repo` scope
- An Anthropic API key

### Installation

```bash
git clone <repo-url>
cd pr-review-agent
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```
GITHUB_TOKEN=ghp_...
ANTHROPIC_API_KEY=sk-ant-...
WEBHOOK_SECRET=<any random string>
SKIP_DRAFT_PRS=true
LOG_LEVEL=INFO
```

### Running locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the server is up:

```bash
curl http://localhost:8000/health
```

### Connecting to GitHub

Use [ngrok](https://ngrok.com/) to expose your local server:

```bash
ngrok http 8000
```

Then add a webhook to your repo under **Settings → Webhooks → Add webhook**:

| Field | Value |
|---|---|
| Payload URL | `https://<ngrok-url>/webhooks/github` |
| Content type | `application/json` |
| Secret | your `WEBHOOK_SECRET` value |
| Events | Pull requests |

Open a PR — the agent will post review comments within a few seconds.

## Tests

```bash
pytest
```

To run a single test file:

```bash
pytest tests/test_llm_reviewer.py -v
```

## Deployment (Fly.io)

```bash
fly launch
fly secrets set GITHUB_TOKEN=ghp_... ANTHROPIC_API_KEY=sk-ant-... WEBHOOK_SECRET=...
fly deploy
```

Set your webhook Payload URL to `https://<your-app>.fly.dev/webhooks/github`.

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | Yes | — | GitHub PAT with `repo` scope |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `WEBHOOK_SECRET` | Yes | — | HMAC secret set in GitHub webhook |
| `SKIP_DRAFT_PRS` | No | `true` | Skip reviews for draft PRs |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `PORT` | No | `8000` | Port to bind the server |
