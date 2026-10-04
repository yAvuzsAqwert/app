"""CORS yapılandırması değişikliği sonrası uygulama bozulmadı (regression).

server.py's CORSMiddleware was changed to combine a CORS_ORIGINS allowlist with an
allow_origin_regex for *.emergentagent.com / *.emergent.host subdomains. This verifies:
  1. A real preflight (OPTIONS) from the preview origin is accepted with a matching
     Access-Control-Allow-Origin header (regex match still works).
  2. An origin that does NOT match the allowlist/regex does not get granted the
     request's origin back (no overly-permissive echo / no injection-style bypass).
  3. The full authenticated flow through the public https preview URL (where Secure
     session cookies are actually usable) still works end-to-end after the CORS change:
     login, /branding (anon), /projects, /dashboard, /reports/monthly?ay=2026-09 all 200.
"""

import os

import httpx

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"

PUBLIC_URL = os.environ.get("PUBLIC_APP_URL", "https://pergola-tracker.preview.emergentagent.com")
PUBLIC_API_URL = f"{PUBLIC_URL}/api"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
BACKEND_API_URL = f"{BACKEND_URL}/api"


def test_cors_preflight_allows_matching_preview_origin():
    # Preflight checked directly against the uvicorn process (bypasses any edge/CDN in
    # front of the public hostname) so we are testing server.py's own CORSMiddleware.
    with httpx.Client(base_url=BACKEND_API_URL, timeout=30.0) as c:
        resp = c.options(
            "/branding",
            headers={
                "Origin": PUBLIC_URL,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200, f"preflight failed: {resp.status_code} {resp.text[:300]}"
        assert resp.headers.get("access-control-allow-origin") == PUBLIC_URL, (
            f"expected allow-origin echo for {PUBLIC_URL}, got headers={dict(resp.headers)}"
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_rejects_unrelated_origin():
    with httpx.Client(base_url=BACKEND_API_URL, timeout=30.0) as c:
        resp = c.options(
            "/branding",
            headers={
                "Origin": "https://evil-attacker.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette's CORSMiddleware returns 400 for a disallowed origin OR 200 without an
        # allow-origin header matching the attacker origin — either way, the attacker origin
        # must never be echoed back as an allowed origin.
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin != "https://evil-attacker.example.com", (
            f"unrelated origin was granted CORS access: {dict(resp.headers)}"
        )


def test_authenticated_flow_still_works_through_public_preview_url():
    with httpx.Client(base_url=PUBLIC_API_URL, timeout=30.0) as c:
        anon_branding = c.get("/branding")
        assert anon_branding.status_code == 200, f"anon /branding failed: {anon_branding.status_code}"

        login = c.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
        assert login.status_code == 200, f"login failed: {login.status_code} {login.text[:300]}"
        assert login.json().get("rol") == "admin"
        assert c.cookies.get("session") is not None or len(c.cookies) > 0, "no session cookie set after login"

        projects = c.get("/projects")
        assert projects.status_code == 200, f"/projects failed: {projects.status_code} {projects.text[:300]}"

        dashboard = c.get("/dashboard")
        assert dashboard.status_code == 200, f"/dashboard failed: {dashboard.status_code} {dashboard.text[:300]}"

        monthly = c.get("/reports/monthly", params={"ay": "2026-09"})
        assert monthly.status_code == 200, f"/reports/monthly failed: {monthly.status_code} {monthly.text[:300]}"
