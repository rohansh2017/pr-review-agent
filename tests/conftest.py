"""Pytest fixtures and test client."""

from unittest.mock import MagicMock

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
