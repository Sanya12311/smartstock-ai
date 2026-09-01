import pyotp


def _enable_2fa_for(client, auth_headers, db_session, test_user):
    """Helper: runs the real setup+enable flow and returns the raw secret."""
    setup = client.post("/auth/2fa/setup", headers=auth_headers).json()
    secret = setup["secret"]
    code = pyotp.TOTP(secret).now()
    response = client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers)
    assert response.status_code == 200
    db_session.refresh(test_user)
    return secret


def test_2fa_setup_requires_auth(client):
    assert client.post("/auth/2fa/setup").status_code == 401


def test_2fa_setup_returns_secret_and_qr_code(client, auth_headers):
    response = client.post("/auth/2fa/setup", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["secret"]) > 0
    assert body["provisioning_uri"].startswith("otpauth://totp/")
    assert len(body["qr_code_base64"]) > 0


def test_2fa_enable_with_correct_code_succeeds(client, auth_headers, db_session, test_user):
    _enable_2fa_for(client, auth_headers, db_session, test_user)
    assert test_user.totp_enabled is True


def test_2fa_enable_with_wrong_code_rejected(client, auth_headers):
    client.post("/auth/2fa/setup", headers=auth_headers)
    response = client.post("/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers)
    assert response.status_code == 400


def test_2fa_enable_without_setup_rejected(client, auth_headers):
    response = client.post("/auth/2fa/enable", json={"code": "123456"}, headers=auth_headers)
    assert response.status_code == 400


def test_2fa_setup_when_already_enabled_rejected(client, auth_headers, db_session, test_user):
    _enable_2fa_for(client, auth_headers, db_session, test_user)
    response = client.post("/auth/2fa/setup", headers=auth_headers)
    assert response.status_code == 400


def test_2fa_disable_wrong_password_rejected(client, auth_headers, db_session, test_user):
    _enable_2fa_for(client, auth_headers, db_session, test_user)
    response = client.post("/auth/2fa/disable", json={"password": "WrongPassword"}, headers=auth_headers)
    assert response.status_code == 400
    db_session.refresh(test_user)
    assert test_user.totp_enabled is True


def test_2fa_disable_correct_password_succeeds(client, auth_headers, db_session, test_user):
    _enable_2fa_for(client, auth_headers, db_session, test_user)
    response = client.post("/auth/2fa/disable", json={"password": "TestPass123"}, headers=auth_headers)
    assert response.status_code == 200
    db_session.refresh(test_user)
    assert test_user.totp_enabled is False
    assert test_user.totp_secret_encrypted is None


def test_login_without_2fa_returns_access_token_directly(client, test_user):
    response = client.post("/auth/login", data={"username": test_user.email, "password": "TestPass123"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] is not None
    assert body["requires_2fa"] is False


def test_login_with_2fa_enabled_requires_second_step(client, auth_headers, db_session, test_user):
    _enable_2fa_for(client, auth_headers, db_session, test_user)

    response = client.post("/auth/login", data={"username": test_user.email, "password": "TestPass123"})
    assert response.status_code == 200
    body = response.json()
    assert body["requires_2fa"] is True
    assert body["access_token"] is None
    assert body["pre_auth_token"]


def test_2fa_verify_login_with_correct_code_succeeds(client, auth_headers, db_session, test_user):
    secret = _enable_2fa_for(client, auth_headers, db_session, test_user)

    login = client.post("/auth/login", data={"username": test_user.email, "password": "TestPass123"}).json()
    code = pyotp.TOTP(secret).now()
    response = client.post(
        "/auth/2fa/verify-login", json={"pre_auth_token": login["pre_auth_token"], "code": code}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_2fa_verify_login_with_wrong_code_rejected(client, auth_headers, db_session, test_user):
    _enable_2fa_for(client, auth_headers, db_session, test_user)

    login = client.post("/auth/login", data={"username": test_user.email, "password": "TestPass123"}).json()
    response = client.post(
        "/auth/2fa/verify-login", json={"pre_auth_token": login["pre_auth_token"], "code": "000000"}
    )
    assert response.status_code == 400


def test_2fa_verify_login_with_garbage_token_rejected(client):
    response = client.post(
        "/auth/2fa/verify-login", json={"pre_auth_token": "not-a-real-token", "code": "123456"}
    )
    assert response.status_code == 401


def test_pre_auth_token_cannot_be_used_as_a_real_session(client, auth_headers, db_session, test_user):
    """Critical security check: the short-lived pre-auth token issued mid-2FA-login
    must never work against a normal protected endpoint, even though it's a
    validly-signed JWT — otherwise 2FA could be bypassed entirely."""
    _enable_2fa_for(client, auth_headers, db_session, test_user)

    login = client.post("/auth/login", data={"username": test_user.email, "password": "TestPass123"}).json()
    pre_auth_token = login["pre_auth_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {pre_auth_token}"})
    assert response.status_code == 401
