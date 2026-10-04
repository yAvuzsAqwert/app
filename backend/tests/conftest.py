"""Pre-scaffolded pytest fixtures for the FastAPI backend.

Tests hit the live uvicorn process managed by supervisor (not an in-process ASGI app), so
the app under test is the same one the frontend and Playwright see. Do NOT re-create this
file — add app-specific fixtures below the marker at the bottom.
"""

import os

import httpx
import pytest
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    """Absolute URL for an /api route: api_url("/status") -> http://localhost:8001/api/status."""
    return f"{API_URL}{path}"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture
def client():
    """Sync httpx client rooted at /api — the default for endpoint tests.

    Example:
        def test_status(client):
            assert client.get("/status").status_code == 200
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture
async def aclient():
    """Async variant, for tests that also await motor/backend helpers directly."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


# --- app-specific fixtures below this line ---

# Session cookies are issued with the `Secure` attribute, so httpx (unlike curl) will not
# resend them over plain http://localhost. Auth-dependent tests must run against the public
# https ingress URL, which proxies to this same backend/Mongo.
PUBLIC_URL = os.environ.get("PUBLIC_APP_URL", "https://pergola-tracker.preview.emergentagent.com")
PUBLIC_API_URL = f"{PUBLIC_URL}/api"


@pytest.fixture
def public_api_url() -> str:
    return PUBLIC_API_URL


@pytest.fixture
def client():  # noqa: F811 - intentional override: auth cookies require https origin
    """Sync httpx client rooted at the public https /api — required for Secure session cookies."""
    with httpx.Client(base_url=PUBLIC_API_URL, timeout=30.0) as c:
        yield c
