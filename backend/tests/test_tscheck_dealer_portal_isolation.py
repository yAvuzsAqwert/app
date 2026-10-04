"""Dealer portal isolation: own project only, 404 on other dealer's project, portal
cookie cannot access team endpoints."""

import httpx

BAYI_EMAIL = "bayi@natura.com"
BAYI_PASSWORD = "bayi123456"


def test_portal_isolation(public_api_url):
    with httpx.Client(base_url=public_api_url, timeout=30.0) as portal_client:
        login = portal_client.post(
            "/portal/login", json={"email": BAYI_EMAIL, "sifre": BAYI_PASSWORD}
        )
        assert login.status_code == 200, login.text[:300]
        assert login.json().get("firma") == "Anadolu Yapı A.Ş."

        ozet = portal_client.get("/portal/ozet")
        assert ozet.status_code == 200
        projeler = ozet.json().get("projeler", [])
        codes = [p["proje_kodu"] for p in projeler]
        assert codes == ["PRG-2026-005"], f"expected only PRG-2026-005, got {codes}"

        own_proforma = portal_client.get("/portal/projeler/PRG-2026-005/proforma")
        assert own_proforma.status_code == 200
        assert own_proforma.headers.get("content-type", "").startswith("application/pdf")

        other_proforma = portal_client.get("/portal/projeler/PRG-2026-001/proforma")
        assert other_proforma.status_code == 404, (
            f"expected 404 for other dealer's project, got {other_proforma.status_code}"
        )

        team_endpoint = portal_client.get("/projects")
        assert team_endpoint.status_code == 401, (
            f"portal cookie must not access /api/projects, got {team_endpoint.status_code}"
        )
