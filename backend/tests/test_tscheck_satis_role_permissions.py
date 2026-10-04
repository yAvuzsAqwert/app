"""Satis role: no user-management permission, limited muhasebe/sandik rights.

Pure permission-matrix check via /api/my-permissions (UI button disabling is covered by a
browser check); this test asserts the authoritative server-side permission set.
"""

SATIS_EMAIL = "ekip@pergola.com"
SATIS_PASSWORD = "Pg-FDq_RcWIcEes"


def test_satis_permission_set(client):
    login = client.post("/auth/login", json={"email": SATIS_EMAIL, "sifre": SATIS_PASSWORD})
    assert login.status_code == 200, login.text[:300]
    assert login.json().get("rol") == "satis"

    perms = client.get("/my-permissions")
    assert perms.status_code == 200
    yetkiler = set(perms.json().get("yetkiler", []))

    # Users & Yetkiler menu is gated by kullanici:yonet -> must be absent for satis.
    assert "kullanici:yonet" not in yetkiler
    # "Muhasebeyi Kaydet" button gated by muhasebe:duzenle -> must be absent.
    assert "muhasebe:duzenle" not in yetkiler
    # "Sandık Ekle" button gated by sandik:yonet -> must be absent.
    assert "sandik:yonet" not in yetkiler
    # Proforma PDF / Kalem Ekle must remain usable.
    assert "proforma:olustur" in yetkiler
    assert "kalem:yonet" in yetkiler
