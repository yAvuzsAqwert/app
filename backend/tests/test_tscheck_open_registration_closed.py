"""SEC-001: anonymous self-registration must be rejected."""


def test_anonymous_register_rejected(client):
    resp = client.post(
        "/auth/register",
        json={
            "email": "tscheck-anonreg-1@example.com",
            "sifre": "TestPass123!",
            "ad_soyad": "TsCheck Anon",
        },
    )
    assert resp.status_code in (401, 403), (
        f"expected 401/403 for anonymous register, got {resp.status_code}: {resp.text[:300]}"
    )

    # Account must not have been created: login with same creds should fail.
    login = client.post(
        "/auth/login",
        json={"email": "tscheck-anonreg-1@example.com", "sifre": "TestPass123!"},
    )
    assert login.status_code in (400, 401), (
        f"account appears to have been created despite rejected register: {login.status_code}"
    )
