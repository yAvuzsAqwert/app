"""PDF çıktılarında Türkçe karakterler bozulmadan çıkar (proforma, sandık etiketleri, dosya.pdf)."""

import io

import pypdf

ADMIN_EMAIL = "yavuz@diagonalventure.com"
ADMIN_PASSWORD = "Diagonal2026!"
PROJECT_ID = "c3a4a793-4e2b-434e-b6e4-834c073696a6"

TURKISH_CHARS = set("ışğüöçİŞÜÖÇ")


def _extract_text(content: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _login(client):
    r = client.post("/auth/login", json={"email": ADMIN_EMAIL, "sifre": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text


def test_proforma_pdf_turkish_characters_intact(client):
    _login(client)
    try:
        r = client.get(f"/projects/{PROJECT_ID}/proforma")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        text = _extract_text(r.content)
        assert TURKISH_CHARS & set(text), "no Turkish-specific characters found in proforma PDF text"
    finally:
        client.post("/auth/logout")


def test_crate_labels_pdf_turkish_characters_intact(client):
    _login(client)
    try:
        r = client.get(f"/projects/{PROJECT_ID}/sandik-etiketleri")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        text = _extract_text(r.content)
        assert TURKISH_CHARS & set(text), "no Turkish-specific characters found in crate-labels PDF text"
    finally:
        client.post("/auth/logout")


def test_project_dossier_pdf_turkish_characters_and_inline_disposition(client):
    _login(client)
    try:
        r = client.get(f"/projects/{PROJECT_ID}/dosya.pdf")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert "inline" in r.headers.get("content-disposition", "")
        text = _extract_text(r.content)
        assert TURKISH_CHARS & set(text), "no Turkish-specific characters found in dossier PDF text"
        assert "PROJE KÜNYESİ" in text or "PROJE KÜNYESİ".replace("İ", "I") in text
    finally:
        client.post("/auth/logout")
