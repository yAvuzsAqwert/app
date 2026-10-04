"""Şifre değiştirme (kendi) ve yönetici şifre sıfırlama (başkası için)."""

import uuid

import httpx

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"


def _admin_login(c: httpx.Client) -> None:
    r = c.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text


def test_change_own_password_validation(client):
    _admin_login(client)
    try:
        bad_current = client.put(
            "/auth/sifre", json={"mevcut_sifre": "kesinlikle-yanlis", "yeni_sifre": "YeniSifre123"}
        )
        assert bad_current.status_code == 401

        too_short = client.put(
            "/auth/sifre", json={"mevcut_sifre": ADMIN_PASSWORD, "yeni_sifre": "short1"}
        )
        assert too_short.status_code == 422
    finally:
        client.post("/auth/logout")


def test_unauthorized_password_change_requires_session(public_api_url):
    with httpx.Client(base_url=public_api_url, timeout=30.0) as anon:
        r = anon.put(
            "/auth/sifre", json={"mevcut_sifre": "x", "yeni_sifre": "YeniSifre123"}
        )
        assert r.status_code == 401


def test_admin_resets_temp_user_password_old_fails_new_works(client, public_api_url):
    _admin_login(client)
    email = f"tscheck-pwreset-{uuid.uuid4().hex[:8]}@example.com"
    old_password = "GeciciSifre1"
    new_password = "YeniSifre2026"
    user_id = None
    try:
        created = client.post(
            "/users",
            json={"email": email, "sifre": old_password, "ad_soyad": "Gecici Kullanici", "rol": "satis"},
        )
        assert created.status_code == 200, created.text
        user_id = created.json()["id"]

        # unauthorized reset: no session at all -> 401
        with httpx.Client(base_url=public_api_url, timeout=30.0) as anon:
            r_anon = anon.put(f"/users/{user_id}/sifre", json={"yeni_sifre": new_password})
            assert r_anon.status_code == 401

        reset = client.put(f"/users/{user_id}/sifre", json={"yeni_sifre": new_password})
        assert reset.status_code == 200, reset.text

        with httpx.Client(base_url=public_api_url, timeout=30.0) as temp_user:
            old_login = temp_user.post("/auth/login", json={"email": email, "sifre": old_password})
            assert old_login.status_code == 401

            new_login = temp_user.post("/auth/login", json={"email": email, "sifre": new_password})
            assert new_login.status_code == 200, new_login.text
            temp_user.post("/auth/logout")
    finally:
        if user_id:
            client.delete(f"/users/{user_id}")
        client.post("/auth/logout")
