"""E-posta + şifre giriş akışı: cookie, case-insensitivity, hatalı giriş, /me, /logout."""

import httpx
import pytest

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"


def test_login_success_sets_httponly_secure_lax_cookie(client, public_api_url):
    r = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["rol"] == "admin"
    set_cookie = r.headers.get("set-cookie", "")
    assert "pergola_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=Lax" in set_cookie
    client.cookies.clear()


def test_login_email_case_insensitive(client):
    r = client.post("/auth/login", json={"email": "YAVUZ@DiagonalVenture.com", "sifre": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == ADMIN_EMAIL
    client.cookies.clear()


def test_wrong_password_and_nonexistent_user_same_message(client):
    r1 = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": "yanlis-sifre-xyz"})
    assert r1.status_code == 401
    msg1 = r1.json()["detail"]

    r2 = client.post(
        "/auth/login", json={"email": "olmayan-kullanici-tscheck@example.com", "sifre": "herhangi1"}
    )
    assert r2.status_code == 401
    msg2 = r2.json()["detail"]
    assert msg1 == msg2


def test_login_empty_body_422(client):
    r = client.post("/auth/login", json={})
    assert r.status_code == 422


def test_me_requires_valid_cookie_then_logout_invalidates(client):
    # no cookie at all
    r_anon = client.get("/auth/me")
    assert r_anon.status_code == 401

    # malformed cookie
    r_bad = client.get("/auth/me", cookies={"pergola_session": "not-a-real-token"})
    assert r_bad.status_code == 401

    # valid login -> /me 200 rol=admin
    login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert login.status_code == 200
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["rol"] == "admin"

    # logout -> 200, then /me -> 401
    out = client.post("/auth/logout")
    assert out.status_code == 200
    me_after = client.get("/auth/me")
    assert me_after.status_code == 401
