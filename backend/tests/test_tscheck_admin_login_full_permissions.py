"""Admin login + full permission set (21 permissions) for yavuz@diagonalventure.com."""

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"


def test_admin_login_and_full_permissions(client):
    login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert login.status_code == 200, f"admin login failed: {login.status_code} {login.text[:300]}"
    body = login.json()
    assert body.get("rol") == "admin"

    perms = client.get("/my-permissions")
    assert perms.status_code == 200
    data = perms.json()
    assert data.get("rol") == "admin"
    yetkiler = data.get("yetkiler", [])
    assert len(yetkiler) == 21, f"expected 21 permissions, got {len(yetkiler)}: {yetkiler}"
