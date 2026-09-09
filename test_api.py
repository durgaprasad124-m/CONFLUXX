from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login():
    email = "test.customer@example.com"
    response = client.post("/auth/register", json={"full_name": "Test Customer", "email": email, "password": "strong-pass-123", "phone": "9876543210", "aadhaar_number": "123456789012"})
    assert response.status_code in {201, 409}
    login = client.post("/auth/login", data={"username": email, "password": "strong-pass-123"})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_password_reset_flow():
    email = f"reset-{uuid4().hex}@example.com"
    client.post("/auth/register", json={"full_name": "Reset User", "email": email, "password": "old-pass-123", "phone": "9876543210", "aadhaar_number": "987654321012"})
    request = client.post("/auth/forgot-password", json={"email": email})
    assert request.status_code == 200
    reset = client.post("/auth/reset-password", json={"token": request.json()["reset_token"], "new_password": "new-pass-123"})
    assert reset.status_code == 200
    login = client.post("/auth/login", data={"username": email, "password": "new-pass-123"})
    assert login.status_code == 200
