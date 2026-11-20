import sqlite3
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.deps import get_db
from api.schema import init_schema
from api.security import hash_password


@pytest.fixture
def api_client():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)

    conn.execute(
        """INSERT INTO clients (code, nom, tel, solde, portail_actif, password_hash)
           VALUES ('CLT-0001', 'Client Officiel', '0555000001', 0.0, 1, ?)""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO vendeurs (code, nom, actif, password_hash, session_salt)
           VALUES ('V1', 'Vendeur Un', 1, ?, 'salt-v1')""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO vendeurs (code, nom, actif, password_hash, session_salt)
           VALUES ('V2', 'Vendeur Deux', 1, ?, 'salt-v2')""",
        (hash_password("Pass12345"),),
    )
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), conn
    finally:
        app.dependency_overrides.clear()
        conn.close()


def test_gps_client_officiel_update_et_lecture(api_client):
    client, conn = api_client
    c_id = conn.execute("SELECT id FROM clients WHERE code='CLT-0001'").fetchone()["id"]

    # Non authentifié -> 401
    assert client.patch(f"/clients/{c_id}/gps", json={"latitude": 36.75, "longitude": 3.05}).status_code == 401

    login_v1 = client.post("/auth/login-vendeur", json={"code_vendeur": "V1", "password": "Pass12345"})
    headers_v1 = {"Authorization": f"Bearer {login_v1.json()['access_token']}"}

    # Coordonnées manquantes -> 400
    assert client.patch(f"/clients/{c_id}/gps", json={}, headers=headers_v1).status_code == 400

    # Mise à jour GPS du client officiel
    res = client.patch(
        f"/clients/{c_id}/gps",
        json={"latitude": 36.7525, "longitude": 3.0419},
        headers=headers_v1,
    )
    assert res.status_code == 200
    assert res.json()["latitude"] == 36.7525
    assert res.json()["longitude"] == 3.0419

    # Visible via GET /clients et GET /clients/me
    liste = client.get("/clients", headers=headers_v1).json()
    clt = next(c for c in liste if c["code"] == "CLT-0001")
    assert clt["latitude"] == 36.7525
    assert clt["longitude"] == 3.0419

    login_c1 = client.post("/auth/login", json={"code_client": "CLT-0001", "password": "Pass12345"})
    me = client.get("/clients/me", headers={"Authorization": f"Bearer {login_c1.json()['access_token']}"}).json()
    assert me["latitude"] == 36.7525
    assert me["longitude"] == 3.0419


def test_gps_prospect_creation_update_et_isolation(api_client):
    client, _ = api_client
    v1_token = client.post("/auth/login-vendeur", json={"code_vendeur": "V1", "password": "Pass12345"}).json()["access_token"]
    v2_token = client.post("/auth/login-vendeur", json={"code_vendeur": "V2", "password": "Pass12345"}).json()["access_token"]
    h_v1 = {"Authorization": f"Bearer {v1_token}"}
    h_v2 = {"Authorization": f"Bearer {v2_token}"}

    # Création d'un prospect avec GPS
    created = client.post(
        "/clients/prospect",
        json={"nom": "Prospect GPS", "wilaya": "Alger", "latitude": 36.71, "longitude": 3.12},
        headers=h_v1,
    )
    assert created.status_code == 201
    p_id = created.json()["id"]
    assert created.json()["latitude"] == 36.71

    # Un autre vendeur ne peut pas modifier le GPS de ce prospect
    assert client.patch(
        f"/clients/prospects/{p_id}/gps",
        json={"latitude": 35.0, "longitude": 2.0},
        headers=h_v2,
    ).status_code == 404

    # V1 met à jour la position GPS du prospect
    updated = client.patch(
        f"/clients/prospects/{p_id}/gps",
        json={"latitude": 36.7222, "longitude": 3.1333},
        headers=h_v1,
    )
    assert updated.status_code == 200
    assert updated.json()["latitude"] == 36.7222
    assert updated.json()["longitude"] == 3.1333


def test_pointage_gps_complete_coordonnees_client_et_prospect(api_client):
    client, conn = api_client
    v1_token = client.post("/auth/login-vendeur", json={"code_vendeur": "V1", "password": "Pass12345"}).json()["access_token"]
    h_v1 = {"Authorization": f"Bearer {v1_token}"}

    c_id = conn.execute("SELECT id FROM clients WHERE code='CLT-0001'").fetchone()["id"]
    prospect = client.post(
        "/clients/prospect",
        json={"nom": "Prospect Sans GPS", "wilaya": "Blida"},
        headers=h_v1,
    ).json()

    # Pointage client officiel sans GPS -> renseigne aussi clients.latitude/longitude
    pt_client = client.post(
        "/tournee/pointage",
        json={"client_id": c_id, "latitude": 36.74, "longitude": 3.08, "observations": "Visite client"},
        headers=h_v1,
    )
    assert pt_client.status_code == 201

    # Pointage prospect sans GPS -> renseigne aussi prospects_clients.latitude/longitude
    pt_prosp = client.post(
        "/tournee/pointage",
        json={"code_client": prospect["code"], "latitude": 36.47, "longitude": 2.83, "observations": "Visite prospect"},
        headers=h_v1,
    )
    assert pt_prosp.status_code == 201

    c_row = conn.execute("SELECT latitude, longitude FROM clients WHERE id=?", (c_id,)).fetchone()
    p_row = conn.execute("SELECT latitude, longitude FROM prospects_clients WHERE id=?", (prospect["id"],)).fetchone()
    assert (c_row["latitude"], c_row["longitude"]) == (36.74, 3.08)
    assert (p_row["latitude"], p_row["longitude"]) == (36.47, 2.83)