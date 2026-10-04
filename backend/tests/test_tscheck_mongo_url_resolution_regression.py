"""Mongo baglanti cozumlemesi degisikligi regresyon yaratmadi.

backend/lib/db.py artik MONGO_URL/MONGODB_URI/MONGO_URI/DATABASE_URL sirasiyla okuyor ve
DB_NAME yoksa 'app' kullaniyor. Bu, uygulamanin bu cozumlemeyle normal calistigini
dogrular: admin girisi 200, GET /api/projects 11 proje, /api/dashboard 200,
/api/reports/monthly?ay=2026-09 200.
"""

import os

import httpx

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"

PUBLIC_URL = os.environ.get("PUBLIC_APP_URL", "https://pergola-tracker.preview.emergentagent.com")
PUBLIC_API_URL = f"{PUBLIC_URL}/api"


def test_db_resolution_supports_full_authenticated_flow_with_seed_counts():
    with httpx.Client(base_url=PUBLIC_API_URL, timeout=30.0) as c:
        login = c.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
        assert login.status_code == 200, f"login failed: {login.status_code} {login.text[:300]}"
        assert login.json().get("rol") == "admin"

        projects = c.get("/projects")
        assert projects.status_code == 200, f"/projects failed: {projects.status_code} {projects.text[:300]}"
        body = projects.json()
        items = body.get("items", body) if isinstance(body, dict) else body
        count = body.get("total") if isinstance(body, dict) and "total" in body else (
            len(items) if isinstance(items, list) else None
        )
        assert count == 11, f"expected 11 seed projects, got {count} (raw keys={list(body)[:10] if isinstance(body, dict) else type(body)})"

        dashboard = c.get("/dashboard")
        assert dashboard.status_code == 200, f"/dashboard failed: {dashboard.status_code} {dashboard.text[:300]}"

        monthly = c.get("/reports/monthly", params={"ay": "2026-09"})
        assert monthly.status_code == 200, f"/reports/monthly failed: {monthly.status_code} {monthly.text[:300]}"
