from fastapi.testclient import TestClient
from uuid import uuid4


def test_data_routes_require_administrator_authentication(database_app) -> None:
    client = TestClient(database_app)

    response = client.get("/api/data/users")

    assert response.status_code == 401
    assert response.json() == {"detail": "Administrator authentication is required."}


def test_user_account_and_vehicle_workflow(database_app, admin_auth_headers) -> None:
    client = TestClient(database_app)

    user_response = client.post(
        "/api/data/users",
        json={"full_name": "Test User", "email": "test.user@example.com"},
        headers=admin_auth_headers,
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    account_response = client.post(
        "/api/data/accounts",
        json={"user_id": user_id, "balance": "25.00", "currency": "MYR"},
        headers=admin_auth_headers,
    )
    assert account_response.status_code == 201
    assert account_response.json()["balance"] == "25.00"

    vehicle_response = client.post(
        "/api/data/vehicles",
        json={"user_id": user_id, "plate_number": "vaa 1234"},
        headers=admin_auth_headers,
    )
    assert vehicle_response.status_code == 201
    assert vehicle_response.json()["plate_number"] == "VAA1234"


def test_missing_parent_returns_meaningful_404(database_app, admin_auth_headers) -> None:
    client = TestClient(database_app)
    response = client.post(
        "/api/data/accounts",
        json={"user_id": "00000000-0000-0000-0000-000000000001", "balance": "5.00"},
        headers=admin_auth_headers,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User was not found."}


def test_duplicate_email_returns_conflict(database_app, admin_auth_headers) -> None:
    client = TestClient(database_app)
    payload = {"full_name": "Test User", "email": "duplicate@example.com"}
    assert (
        client.post("/api/data/users", json=payload, headers=admin_auth_headers).status_code == 201
    )
    response = client.post("/api/data/users", json=payload, headers=admin_auth_headers)
    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this email already exists."}


def test_invalid_currency_is_rejected_before_database(database_app, admin_auth_headers) -> None:
    client = TestClient(database_app)
    response = client.post(
        "/api/data/accounts",
        json={
            "user_id": "00000000-0000-0000-0000-000000000001",
            "balance": "5.00",
            "currency": "USD",
        },
        headers=admin_auth_headers,
    )
    assert response.status_code == 422


def test_simulated_wallet_top_up_creates_an_auditable_ledger_entry(database_app, admin_auth_headers) -> None:
    client = TestClient(database_app)
    user_response = client.post(
        "/api/data/users", json={"full_name": "Wallet User", "email": f"wallet{uuid4().hex[:12]}@example.com"},
        headers=admin_auth_headers,
    )
    assert user_response.status_code == 201, user_response.text
    user = user_response.json()
    account = client.post(
        "/api/data/accounts", json={"user_id": user["id"], "balance": "5.00"},
        headers=admin_auth_headers,
    ).json()
    response = client.post(
        f"/api/data/accounts/{account['id']}/top-ups",
        json={"amount": "12.50", "idempotency_key": "wallet-topup-0001"},
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["balance"] == "17.50"
    ledger = client.get(f"/api/data/accounts/{account['id']}/ledger", headers=admin_auth_headers)
    assert ledger.status_code == 200
    assert {entry["entry_type"] for entry in ledger.json()} == {"top_up", "opening_balance"}
