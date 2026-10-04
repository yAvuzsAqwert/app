"""SEC-003: monthly report period validation (regex ^\\d{4}-(0[1-9]|1[0-2])$)."""

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"


def test_monthly_report_period_validation(client):
    login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert login.status_code == 200, login.text[:300]

    bad1 = client.get("/reports/monthly", params={"ay": "2026-"})
    assert bad1.status_code == 400, f"expected 400, got {bad1.status_code}: {bad1.text[:200]}"

    bad2 = client.get("/reports/monthly", params={"ay": "2026-13"})
    assert bad2.status_code == 400, f"expected 400, got {bad2.status_code}: {bad2.text[:200]}"

    good = client.get("/reports/monthly", params={"ay": "2026-09"})
    assert good.status_code == 200, f"expected 200, got {good.status_code}: {good.text[:200]}"
    body = good.json()
    assert "kur_dagilimi" in body and body["kur_dagilimi"], "kur_dagilimi should be populated"
    assert "try_satis" in body
