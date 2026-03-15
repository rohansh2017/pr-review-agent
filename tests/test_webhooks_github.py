"""Tests for GitHub webhook handler (signature verification and payload handling)."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.webhooks.github import verify_signature


def test_verify_signature_valid():
    secret = "my_secret"
    body = b'{"action":"opened","repository":{"full_name":"o/r"},"pull_request":{"number":1}}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, secret) is True


def test_verify_signature_invalid_secret():
    body = b"{}"
    sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, "wrong_secret") is False


def test_verify_signature_missing_prefix():
    body = b"{}"
    assert verify_signature(body, "invalid", "s") is False


def test_webhook_returns_401_without_valid_signature(client: TestClient):
    payload = {"action": "opened", "repository": {"full_name": "o/r"}, "pull_request": {"number": 1}}
    resp = client.post("/webhooks/github", json=payload)
    assert resp.status_code == 401


def test_webhook_returns_200_with_valid_signature_and_schedules_review(client: TestClient):
    """With valid signature and pull_request payload, webhook returns 200 (review runs in background)."""
    secret = "test_secret"
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 42, "title": "Fix bug", "body": None, "draft": False},
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "pull_request",
        },
    )
    assert resp.status_code == 200
    assert resp.content == b"ok"
