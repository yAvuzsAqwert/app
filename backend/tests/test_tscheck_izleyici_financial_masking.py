"""SEC-002: izleyici (view-only) role must not see financial data.

Creates its own tscheck- prefixed izleyici user via the admin account, verifies masking,
then deletes the user it created (fixture discipline).
"""

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"
TEST_EMAIL = "tscheck-izleyici-sec002@example.com"
TEST_PASSWORD = "TestPass123!"


def _admin_client(client):
    r = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text


def test_admin_dashboard_unaffected_by_masking(client):
    """Same request for the admin account must keep returning real figures."""
    _admin_client(client)
    dash = client.get("/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert body.get("toplam_satis", 0) > 2_000_000
    asamalar = body.get("asamalar", [])
    assert any(a.get("tutar", 0) > 0 for a in asamalar)


def test_izleyici_cannot_see_financials(client):
    _admin_client(client)

    created = client.post(
        "/users",
        json={
            "email": TEST_EMAIL,
            "sifre": TEST_PASSWORD,
            "ad_soyad": "TsCheck Izleyici SEC002",
            "rol": "izleyici",
        },
    )
    assert created.status_code in (200, 201), created.text[:300]
    user_id = created.json()["id"]

    try:
        # Separate client for the izleyici session (cookies are per-client here, so use a new one).
        import httpx

        with httpx.Client(base_url=client.base_url, timeout=30.0) as izleyici_client:
            login = izleyici_client.post(
                "/auth/login", json={"email": TEST_EMAIL, "sifre": TEST_PASSWORD}
            )
            assert login.status_code == 200, login.text[:300]

            dash = izleyici_client.get("/dashboard")
            assert dash.status_code == 200
            dash_body = dash.json()
            assert dash_body.get("toplam_satis") == 0
            assert dash_body.get("net_kar") == 0

            # Full breakdown masking (iteration_1 follow-up fix): asamalar[].tutar,
            # para_birimi_dagilimi[].tutar and yaklasan_sevkiyatlar[].muhasebe must all be 0,
            # while asamalar[].adet counts stay intact.
            asamalar = dash_body.get("asamalar", [])
            assert len(asamalar) > 0
            assert all(a.get("tutar") == 0 for a in asamalar), asamalar
            assert any(a.get("adet", 0) > 0 for a in asamalar), "adet counts should remain visible"

            pbd = dash_body.get("para_birimi_dagilimi", [])
            assert len(pbd) > 0
            assert all(p.get("tutar") == 0 for p in pbd), pbd

            ys = dash_body.get("yaklasan_sevkiyatlar", [])
            assert len(ys) > 0
            for shipment in ys:
                muhasebe_ys = shipment.get("muhasebe", {})
                for key, val in muhasebe_ys.items():
                    if isinstance(val, (int, float)):
                        assert val == 0, f"{key} not masked: {val}"
                    elif isinstance(val, list):  # odemeler
                        for payment in val:
                            assert payment.get("tutar", 0) == 0

            projects = izleyici_client.get("/projects", params={"q": "Nice"})
            assert projects.status_code == 200
            plist = projects.json()
            assert len(plist) >= 1, "expected PRG-2026-002 (Nice) in results"
            proj = plist[0]
            muhasebe = proj.get("muhasebe", {})
            assert muhasebe.get("satis", 0) == 0
            assert muhasebe.get("net_kar", 0) == 0
            proj_id = proj["id"]

            detail = izleyici_client.get(f"/projects/{proj_id}")
            assert detail.status_code == 200
            detail_body = detail.json()
            detail_muhasebe = detail_body.get("project", detail_body).get("muhasebe", {})
            assert detail_muhasebe.get("satis", 0) == 0
            assert detail_muhasebe.get("net_kar", 0) == 0

            dealers = izleyici_client.get("/dealers")
            assert dealers.status_code == 403, f"expected 403, got {dealers.status_code}"

            evraklar = izleyici_client.get(f"/projects/{proj_id}/evraklar")
            assert evraklar.status_code == 403, f"expected 403, got {evraklar.status_code}"

            indir = izleyici_client.get("/evraklar/does-not-matter/indir")
            assert indir.status_code == 403, f"expected 403, got {indir.status_code}"
    finally:
        # cleanup the user this test created
        client.delete(f"/users/{user_id}")
