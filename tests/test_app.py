from uuid import uuid4


def test_index_loads():
    from app import app

    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"LANDLORDPRO" in response.data


def test_register_and_login_landlord_dashboard():
    from app import app

    client = app.test_client()

    email = f"landlord-{uuid4().hex}@example.com"
    password = "StrongPass123"

    client.post(
        "/auth/register",
        data={
            "fullname": "Test Landlord",
            "email": email,
            "phone": "+254700000000",
            "role": "landlord",
            "password": password,
        },
        follow_redirects=True,
    )

    response = client.post(
        "/auth/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Landlord Dashboard" in response.data


def test_jwt_api_login_and_me():
    from app import app

    client = app.test_client()

    email = f"tenant-{uuid4().hex}@example.com"
    password = "StrongPass123"

    client.post(
        "/auth/register",
        data={
            "fullname": "Test Tenant",
            "email": email,
            "phone": "+254711111111",
            "role": "tenant",
            "password": password,
        },
        follow_redirects=True,
    )

    response = client.post(
        "/api/v1/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    token = response.get_json()["token"]

    response = client.get(
        "/api/v1/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["role"] == "tenant"