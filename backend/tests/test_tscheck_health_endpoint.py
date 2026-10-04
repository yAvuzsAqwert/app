"""Yeni /api/health tesis ucu.

GET /api/health oturum gerekmeden 200 doner ve {ok, db, kullanici, proje} seklinde bir
govde verir; MONGO_URL/sifre gibi gizli bilgi icermez.
"""

import os

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
BACKEND_API_URL = f"{BACKEND_URL}/api"

SECRET_MARKERS = ("mongodb://", "mongodb+srv://", "MONGO_URL", "sifre", "password", "PASSWORD")


def test_health_endpoint_no_session_required_and_shape():
    with httpx.Client(base_url=BACKEND_API_URL, timeout=30.0) as c:
        resp = c.get("/health")  # no cookies/auth attached
        assert resp.status_code == 200, f"/health failed: {resp.status_code} {resp.text[:300]}"
        body = resp.json()
        assert body.get("ok") is True
        assert body.get("db") == "up"
        assert isinstance(body.get("kullanici"), int) and body["kullanici"] >= 3
        assert isinstance(body.get("proje"), int) and body["proje"] >= 11

        raw = resp.text
        for marker in SECRET_MARKERS:
            assert marker not in raw, f"health response leaked secret-looking marker: {marker}"
