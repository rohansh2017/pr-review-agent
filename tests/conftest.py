"""Pytest fixtures and test client."""

import os
from unittest.mock import MagicMock

# App startup loads Settings from the environment, so a clean checkout needs dummy values.
for _k in ("GITHUB_TOKEN", "ANTHROPIC_API_KEY", "WEBHOOK_SECRET"):
    os.environ.setdefault(_k, "test")

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_review_service, get_settings


@pytest.fixture
def client() -> TestClient:
    """Test client with dependencies overridden so tests don't require real env."""
    app.dependency_overrides[get_settings] = lambda: Settings(
        github_token="test",
        anthropic_api_key="test",
        webhook_secret="test_secret",
    )
    app.dependency_overrides[get_review_service] = lambda: MagicMock()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
