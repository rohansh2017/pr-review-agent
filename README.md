# PR Review Agent

A GitHub webhook service that reviews pull requests with Claude and posts inline comments on the diff: bugs, security issues and missing tests.

<!-- TODO: screenshot or GIF of the bot commenting on a real PR -->

## How it works

```
GitHub PR event ──▶ FastAPI /webhooks/github ──▶ background task
                         │ verify HMAC, return 200        │
                         ▼                                ▼
                                           GitHub files API (diff)
                                                          ▼
                                           Claude (JSON comments)
                                                          ▼
                                           GitHub review API (inline comments)
```

1. GitHub sends a `pull_request` webhook (`opened` or `synchronize`).
2. The service verifies the HMAC-SHA256 signature and returns `200` immediately.
3. A background task fetches the changed files and their patches through the GitHub API and sends them to Claude.
4. Claude returns a JSON array of comments (`path`, `line`, `body`, optional severity); the service posts them as one review with inline comments.

## Stack

FastAPI, LangChain + Anthropic, httpx, Pydantic, Docker, Fly.io. Tests use pytest and respx.

## Design decisions

- **Acknowledge first, review later.** GitHub expects a fast webhook response, so the handler returns `200` and the review runs in an `asyncio` task.
- **Retries with backoff.** A failed review is retried up to 3 times (1s, 2s, 4s) before it is logged and dropped.
- **Per-PR rate limit.** A PR is reviewed at most once every 60 seconds, so a burst of pushes does not trigger a burst of reviews.
- **Defensive parsing.** The model's response is searched for a JSON array, and any comment missing a path, line or body is discarded rather than posted.
- **Draft PRs skipped by default** (`SKIP_DRAFT_PRS`).

## Run it

Requires Python 3.10+, a GitHub personal access token with `repo` scope, and an Anthropic API key.

```bash
git clone https://github.com/rohansh2017/pr-review-agent.git
cd pr-review-agent
pip install -r requirements.txt
cp .env.example .env   # then fill in the three secrets
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check it is up:

```bash
curl http://localhost:8000/health
```

### Connect it to a repo

Expose the local server with [ngrok](https://ngrok.com/) (`ngrok http 8000`), then add a webhook under **Settings → Webhooks → Add webhook**:

| Field | Value |
|---|---|
| Payload URL | `https://<ngrok-url>/webhooks/github` |
| Content type | `application/json` |
| Secret | your `WEBHOOK_SECRET` value |
| Events | Pull requests |

Open a PR and the agent posts its review comments.

## Tests

```bash
pytest
```

Covers webhook signature verification and event filtering, the GitHub client, response parsing in the LLM reviewer, and the review service.

## Deploy (Fly.io)

```bash
fly launch
fly secrets set GITHUB_TOKEN=... ANTHROPIC_API_KEY=... WEBHOOK_SECRET=...
fly deploy
```

Set the webhook Payload URL to `https://<your-app>.fly.dev/webhooks/github`.

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | Yes | | GitHub PAT with `repo` scope |
| `ANTHROPIC_API_KEY` | Yes | | Anthropic API key |
| `WEBHOOK_SECRET` | Yes | | HMAC secret set in the GitHub webhook |
| `SKIP_DRAFT_PRS` | No | `true` | Skip reviews for draft PRs |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `PORT` | No | `8000` | Port to bind the server |

## Limitations

- Only the first page of changed files is fetched, so very large PRs are reviewed partially.
- The model sees the diff only, not the rest of the repository.
- The rate limiter is in memory: it resets on restart and is not shared across instances.
- There is no cap on diff size before it is sent to the model.
