from fastapi.testclient import TestClient


def test_user_account_and_vehicle_workflow(database_app) -> None:
    client = TestClient(database_app)

    user_response = client.post(
        "/api/data/users",
        json={"full_name": "Test User", "email": "test.user@example.com"},
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    account_response = client.post(
        "/api/data/accounts", json={"user_id": user_id, "balance": "25.00", "currency": "MYR"}
    )
    assert account_response.status_code == 201
    assert account_response.json()["balance"] == "25.00"

    vehicle_response = client.post(
        "/api/data/vehicles", json={"user_id": user_id, "plate_number": "vaa 1234"}
    )
    assert vehicle_response.status_code == 201
    assert vehicle_response.json()["plate_number"] == "VAA1234"


def test_missing_parent_returns_meaningful_404(database_app) -> None:
    client = TestClient(database_app)
    response = client.post(
        "/api/data/accounts",
        json={"user_id": "00000000-0000-0000-0000-000000000001", "balance": "5.00"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User was not found."}


def test_duplicate_email_returns_conflict(database_app) -> None:
    client = TestClient(database_app)
    payload = {"full_name": "Test User", "email": "duplicate@example.com"}
    assert client.post("/api/data/users", json=payload).status_code == 201
    response = client.post("/api/data/users", json=payload)
    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this email already exists."}


def test_invalid_currency_is_rejected_before_database(database_app) -> None:
    client = TestClient(database_app)
    response = client.post(
        "/api/data/accounts",
        json={
            "user_id": "00000000-0000-0000-0000-000000000001",
            "balance": "5.00",
            "currency": "USD",
        },
    )
    assert response.status_code == 422
