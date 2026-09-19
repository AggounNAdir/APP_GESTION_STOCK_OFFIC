"""
Tests unitaires et d'intégration pour l'API Portail Client (FastAPI).
Utilise TestClient de FastAPI avec la base de données réelle (gestion_stock.db).
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.db import get_conn, init_db
from api.security import hash_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    # S'assurer qu'un client de test existe dans la base
    conn = get_conn()
    try:
        # Vérifier si CLT-TEST existe
        row = conn.execute("SELECT id FROM clients WHERE code='CLT-TEST'").fetchone()
        if not row:
            conn.execute(
                """INSERT INTO clients (code, nom, tel, solde, password_hash, portail_actif)
                   VALUES ('CLT-TEST', 'Client Test API', '0600000000', 0.0, ?, 1)""",
                (hash_password("Pass12345"),)
            )
        else:
            conn.execute(
                "UPDATE clients SET password_hash=?, portail_actif=1 WHERE code='CLT-TEST'",
                (hash_password("Pass12345"),)
            )
        conn.commit()
    finally:
        conn.close()
    yield


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success():
    response = client.post(
        "/auth/login",
        json={"code_client": "CLT-TEST", "password": "Pass12345"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password():
    response = client.post(
        "/auth/login",
        json={"code_client": "CLT-TEST", "password": "MauvaisMotDePasse"}
    )
    assert response.status_code == 401


def test_client_me_unauthorized():
    response = client.get("/clients/me")
    assert response.status_code == 401


def test_client_me_authorized():
    # Login pour obtenir le token
    login_res = client.post(
        "/auth/login",
        json={"code_client": "CLT-TEST", "password": "Pass12345"}
    )
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/clients/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "CLT-TEST"
    assert data["nom"] == "Client Test API"


def test_catalogue_produits():
    login_res = client.post(
        "/auth/login",
        json={"code_client": "CLT-TEST", "password": "Pass12345"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/produits", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
