"""Brute-force koruması: email+IP bazlı 10 deneme sonrası 429, diğer hesap etkilenmez."""

import uuid

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"


def test_brute_force_locks_after_ten_then_other_account_still_works(client):
    fake_email = f"tscheck-bruteforce-{uuid.uuid4().hex[:10]}@example.com"

    statuses = []
    for _ in range(10):
        r = client.post("/auth/login", json={"email": fake_email, "sifre": "wrong-pass-1"})
        statuses.append(r.status_code)
    assert all(s == 401 for s in statuses), statuses

    r11 = client.post("/auth/login", json={"email": fake_email, "sifre": "wrong-pass-1"})
    assert r11.status_code == 429, r11.text
    assert "15 dakika" in r11.json()["detail"]

    # second lockout check stays 429 too
    r12 = client.post("/auth/login", json={"email": fake_email, "sifre": "wrong-pass-1"})
    assert r12.status_code == 429

    # a completely different, valid account can still log in during the fake email's lockout
    ok = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert ok.status_code == 200, ok.text
    assert ok.json()["rol"] == "admin"
    client.cookies.clear()

    # the locked-out address was never a real user — no row created, no persistent account damage
    # (no users.find_one side effect possible since /auth/login never creates user rows)
