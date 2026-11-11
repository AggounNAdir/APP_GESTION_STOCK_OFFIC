import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schema import init_schema
from api.security import hash_password


@pytest.fixture
def api_client():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    conn.execute(
        """INSERT INTO clients(code, nom, portail_actif, password_hash)
           VALUES ('C1', 'Client Un', 1, ?)""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO clients(code, nom, portail_actif)
           VALUES ('C2', 'Client Deux', 1)"""
    )
    conn.execute(
        """INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt)
           VALUES ('V1', 'Vendeur Un', 1, ?, 'session-1')""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt)
           VALUES ('V2', 'Vendeur Deux', 1, ?, 'session-2')""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut)
           VALUES ('PR1', 'Prospect Un', 1, '2026-11-10', 'Nouveau')"""
    )
    conn.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut)
           VALUES ('PR2', 'Prospect Deux', 2, '2026-11-10', 'Nouveau')"""
    )
    client_id = conn.execute(
        "SELECT id FROM clients WHERE code='C1'"
    ).fetchone()["id"]
    client_autre_id = conn.execute(
        "SELECT id FROM clients WHERE code='C2'"
    ).fetchone()["id"]
    prospect_id = conn.execute(
        "SELECT id FROM prospects_clients WHERE code='PR1'"
    ).fetchone()["id"]
    conn.execute(
        """INSERT INTO versements_clients(numero, date_vers, client_id, montant, vendeur_id)
           VALUES ('VC1', '2026-11-10', ?, 100, 1)""",
        (client_id,),
    )
    conn.execute(
        """INSERT INTO versements_prospects(numero, date_vers, prospect_id, montant, vendeur_id)
           VALUES ('VP1', '2026-11-09', ?, 50, 1)""",
        (prospect_id,),
    )
    conn.execute(
        """INSERT INTO versements_clients(numero, date_vers, client_id, montant, vendeur_id)
           VALUES ('VC2', '2026-11-10', ?, 999, 2)""",
        (client_autre_id,),
    )
    conn.commit()

    def override_get_db():
        yield conn

    from api.deps import get_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), conn
    app.dependency_overrides.clear()
    conn.close()


def test_seller_can_refresh_versements_and_only_sees_own_receipts(api_client):
    client, _ = api_client
    login = client.post(
        "/auth/login-vendeur",
        json={"code_vendeur": "V1", "password": "Pass12345"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get("/versements", headers=headers)

    assert response.status_code == 200
    assert [row["numero"] for row in response.json()] == ["VC1", "VP1"]
    assert response.json()[0]["nom_client"] == "Client Un"
    assert response.json()[0]["code_client"] == "C1"
    assert response.json()[1]["nom_client"] == "Prospect Un"
    assert response.json()[1]["prospect_id"] is not None


def test_seller_versements_still_require_valid_seller_session(api_client):
    client, conn = api_client
    login = client.post(
        "/auth/login-vendeur",
        json={"code_vendeur": "V1", "password": "Pass12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    conn.execute("UPDATE vendeurs SET session_salt='revoked' WHERE id=1")
    conn.commit()

    assert client.get("/versements", headers=headers).status_code == 401
    assert client.get("/versements").status_code == 401


def test_client_still_sees_only_own_versements(api_client):
    client, _ = api_client
    login = client.post(
        "/auth/login",
        json={"code_client": "C1", "password": "Pass12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get("/versements", headers=headers)

    assert response.status_code == 200
    assert [row["numero"] for row in response.json()] == ["VC1"]


def test_versement_creation_requires_authentication(api_client):
    client, conn = api_client

    response = client.post(
        "/versements",
        json={"client_id": 1, "montant": 25},
    )

    assert response.status_code == 401
    assert conn.execute(
        "SELECT COUNT(*) FROM versements_clients WHERE numero LIKE 'VC-%'"
    ).fetchone()[0] == 0


def test_client_can_only_record_payment_for_own_account(api_client):
    client, conn = api_client
    login = client.post(
        "/auth/login",
        json={"code_client": "C1", "password": "Pass12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client_id = conn.execute(
        "SELECT id FROM clients WHERE code='C1'"
    ).fetchone()["id"]
    another_client_id = conn.execute(
        "SELECT id FROM clients WHERE code='C2'"
    ).fetchone()["id"]

    own_payment = client.post(
        "/versements",
        json={"client_id": client_id, "montant": 25},
        headers=headers,
    )
    another_payment = client.post(
        "/versements",
        json={"client_id": another_client_id, "montant": 25},
        headers=headers,
    )

    assert own_payment.status_code == 201
    assert another_payment.status_code == 403


def test_seller_payment_uses_authenticated_seller_and_positive_amount(api_client):
    client, conn = api_client
    login = client.post(
        "/auth/login-vendeur",
        json={"code_vendeur": "V1", "password": "Pass12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client_id = conn.execute(
        "SELECT id FROM clients WHERE code='C2'"
    ).fetchone()["id"]

    payment = client.post(
        "/versements",
        json={"client_id": client_id, "montant": 25, "vendeur_id": 2},
        headers=headers,
    )
    invalid_payment = client.post(
        "/versements",
        json={"client_id": client_id, "montant": -25},
        headers=headers,
    )

    assert payment.status_code == 201
    saved_vendeur_id = conn.execute(
        "SELECT vendeur_id FROM versements_clients WHERE id=?",
        (payment.json()["id"],),
    ).fetchone()["vendeur_id"]
    assert saved_vendeur_id == 1
    assert invalid_payment.status_code == 422


def test_sensitive_lists_require_seller_auth_and_are_scoped(api_client):
    client, _ = api_client

    protected_paths = (
        "/clients",
        "/tournee/pointages",
        "/admin/vendeurs",
        "/admin/ventes-vendeurs",
        "/admin/situation-journaliere-vendeurs",
    )
    for path in protected_paths:
        assert client.get(path).status_code == 401

    login = client.post(
        "/auth/login-vendeur",
        json={"code_vendeur": "V1", "password": "Pass12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    sellers = client.get("/admin/vendeurs", headers=headers)
    assert sellers.status_code == 200
    assert [row["code"] for row in sellers.json()] == ["V1"]
    assert "session_salt" not in sellers.json()[0]
    assert "password_hash" not in sellers.json()[0]
    assert client.get(
        "/admin/ventes-vendeurs?vendeur_id=2", headers=headers
    ).status_code == 403
    assert client.get(
        "/tournee/pointages?vendeur_id=2", headers=headers
    ).status_code == 403
