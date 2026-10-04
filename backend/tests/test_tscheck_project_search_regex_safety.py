"""Project search must not be vulnerable to regex-DoS / regex injection (re.escape applied)."""

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"


def test_project_search_no_regex_injection(client):
    login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert login.status_code == 200, login.text[:300]

    evil = client.get("/projects", params={"q": "((((a+)+)+)+)+$"})
    assert evil.status_code == 200, f"expected 200 (no 500), got {evil.status_code}: {evil.text[:200]}"
    assert isinstance(evil.json(), list)

    normal = client.get("/projects", params={"q": "Nice"})
    assert normal.status_code == 200
    codes = [p["proje_kodu"] for p in normal.json()]
    assert "PRG-2026-002" in codes, f"expected PRG-2026-002 in results, got {codes}"
