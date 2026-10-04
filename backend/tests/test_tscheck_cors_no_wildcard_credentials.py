"""Kimlik bilgili CORS artik wildcard kullanmiyor.

Canli domain (siparis.diagonalventure.com) hatasinin kod tarafi duzeltmesini dogrular:
  1. OPTIONS /api/projects, Origin: https://siparis.diagonalventure.com ile -> yanitta
     access-control-allow-origin TAM olarak bu origin, allow-credentials: true.
  2. OPTIONS /api/projects, Origin: https://kotu-site.example ile -> allow-origin header
     HIC donmez (reddedilir).
  3. Hicbir senaryoda "access-control-allow-origin: *" donmez.
"""

import os

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
BACKEND_API_URL = f"{BACKEND_URL}/api"

ALLOWED_ORIGIN = "https://siparis.diagonalventure.com"
BAD_ORIGIN = "https://kotu-site.example"


def test_preflight_allows_exact_custom_domain_with_credentials():
    with httpx.Client(base_url=BACKEND_API_URL, timeout=30.0) as c:
        resp = c.options(
            "/projects",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert resp.status_code == 200, f"preflight failed: {resp.status_code} {resp.text[:300]}"
        assert allow_origin == ALLOWED_ORIGIN, (
            f"expected exact echo of {ALLOWED_ORIGIN}, got {allow_origin!r} headers={dict(resp.headers)}"
        )
        assert allow_origin != "*", "wildcard origin returned for a credentialed request"
        assert resp.headers.get("access-control-allow-credentials") == "true"


def test_preflight_rejects_unrelated_origin_no_header_at_all():
    with httpx.Client(base_url=BACKEND_API_URL, timeout=30.0) as c:
        resp = c.options(
            "/projects",
            headers={
                "Origin": BAD_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin is None, (
            f"unrelated origin {BAD_ORIGIN} should get NO allow-origin header, got {allow_origin!r}"
        )
        assert allow_origin != "*"


def test_no_response_ever_echoes_wildcard_star():
    with httpx.Client(base_url=BACKEND_API_URL, timeout=30.0) as c:
        for origin in (ALLOWED_ORIGIN, BAD_ORIGIN, "https://pergola-tracker.preview.emergentagent.com"):
            resp = c.options(
                "/projects",
                headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
            )
            assert resp.headers.get("access-control-allow-origin") != "*", (
                f"wildcard allow-origin leaked for Origin={origin}"
            )
