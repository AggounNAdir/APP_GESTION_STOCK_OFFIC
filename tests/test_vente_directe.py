import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.deps import get_db
from api.main import app
from api.schema import init_schema
from api.security import hash_password
from api.vendeur_dossier import ventes_vendeur


@pytest.fixture
def api_client():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    conn.execute(
        """INSERT INTO clients(code, nom, portail_actif, password_hash)
           VALUES ('C1', 'Client Un', 1, ?)""",
        (hash_password("Client123"),),
    )
    conn.execute(
        """UPDATE clients SET portail_actif=1, password_hash=?
           WHERE code='CLT-COMPTOIR'""",
        (hash_password("Comptoir123"),),
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
    conn.execute(
        """INSERT INTO produits
           (code, designation, unite, facteur_conversion, prix_vente, stock_actuel, actif)
           VALUES ('PRD1', 'Produit Un', 'Carton', 12, 10, 100, 1)"""
    )
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='V1'").fetchone()["id"]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD1'").fetchone()["id"]
    conn.execute(
        """INSERT INTO stock_camion_vendeur
           (vendeur_id, produit_id, quantite_colis, quantite_pieces)
           VALUES (?, ?, 2, 24)""",
        (vendeur_id, produit_id),
    )
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), conn
    app.dependency_overrides.clear()
    conn.close()


def _seller_headers(client):
    login = client.post(
        "/auth/login-vendeur",
        json={"code_vendeur": "V1", "password": "Pass12345"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_direct_sale_records_prospect_partial_payment_and_decrements_truck(api_client):
    client, conn = api_client
    headers = _seller_headers(client)
    prospect_id = conn.execute(
        "SELECT id FROM prospects_clients WHERE code='PR1'"
    ).fetchone()["id"]
    produit_id = conn.execute(
        "SELECT id FROM produits WHERE code='PRD1'"
    ).fetchone()["id"]

    response = client.post(
        "/tournee/vente-directe",
        headers=headers,
        json={
            "is_prospect": True,
            "prospect_id": prospect_id,
            "lignes": [{"produit_id": produit_id, "quantite": 1, "prix_unitaire": 10}],
            "montant_verse": 50,
            "mode_reglement": "Espèces",
        },
    )

    assert response.status_code == 201
    sale = response.json()
    assert sale["total"] == 120
    assert sale["montant_verse"] == 50
    assert sale["reste_payer"] == 70

    bon = conn.execute(
        "SELECT client_id, prospect_id, vendeur_id FROM bons_vente WHERE id=?",
        (sale["bon_vente_id"],),
    ).fetchone()
    assert bon["prospect_id"] == prospect_id
    assert bon["vendeur_id"] == 1
    assert conn.execute(
        "SELECT solde FROM prospects_clients WHERE id=?", (prospect_id,)
    ).fetchone()["solde"] == 70
    assert conn.execute(
        "SELECT montant FROM versements_prospects WHERE prospect_id=?",
        (prospect_id,),
    ).fetchone()["montant"] == 50
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=1 AND produit_id=?",
        (produit_id,),
    ).fetchone()) == (1, 12)

    history = client.get("/tournee/ventes", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["client_nom"] == "Prospect Un"
    assert history.json()[0]["numero"] == sale["numero"]
    assert history.json()[0]["reste_payer"] == 70
    assert ventes_vendeur(conn, 1)[0]["client"] == "Prospect Un"

    comptoir_login = client.post(
        "/auth/login",
        json={"code_client": "CLT-COMPTOIR", "password": "Comptoir123"},
    )
    comptoir_headers = {
        "Authorization": f"Bearer {comptoir_login.json()['access_token']}"
    }
    assert client.get("/clients/me/ventes", headers=comptoir_headers).json() == []


def test_direct_sale_to_client_records_full_payment(api_client):
    client, conn = api_client
    headers = _seller_headers(client)
    produit_id = conn.execute(
        "SELECT id FROM produits WHERE code='PRD1'"
    ).fetchone()["id"]

    response = client.post(
        "/tournee/vente-directe",
        headers=headers,
        json={
            "code_client": "C1",
            "lignes": [{"produit_id": produit_id, "quantite": 1, "prix_unitaire": 10}],
            "montant_verse": 120,
            "mode_reglement": "Carte",
        },
    )

    assert response.status_code == 201
    assert response.json()["reste_payer"] == 0
    client_id = conn.execute(
        "SELECT id FROM clients WHERE code='C1'"
    ).fetchone()["id"]
    assert conn.execute(
        "SELECT COUNT(*) FROM versements_clients WHERE client_id=? AND montant=120",
        (client_id,),
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM bons_vente WHERE client_id=? AND prospect_id IS NULL",
        (client_id,),
    ).fetchone()[0] == 1


def test_direct_sale_rejects_insufficient_truck_stock_without_creating_sale(api_client):
    client, conn = api_client
    headers = _seller_headers(client)
    prospect_id = conn.execute(
        "SELECT id FROM prospects_clients WHERE code='PR1'"
    ).fetchone()["id"]
    produit_id = conn.execute(
        "SELECT id FROM produits WHERE code='PRD1'"
    ).fetchone()["id"]

    response = client.post(
        "/tournee/vente-directe",
        headers=headers,
        json={
            "is_prospect": True,
            "prospect_id": prospect_id,
            "lignes": [{"produit_id": produit_id, "quantite": 3, "prix_unitaire": 10}],
            "montant_verse": 0,
        },
    )

    assert response.status_code == 409
    assert conn.execute("SELECT COUNT(*) FROM bons_vente").fetchone()[0] == 0
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=1 AND produit_id=?",
        (produit_id,),
    ).fetchone()) == (2, 24)


def test_direct_sale_rejects_overpayment_and_foreign_seller_prospect(api_client):
    client, conn = api_client
    headers = _seller_headers(client)
    foreign_prospect_id = conn.execute(
        "SELECT id FROM prospects_clients WHERE code='PR2'"
    ).fetchone()["id"]
    produit_id = conn.execute(
        "SELECT id FROM produits WHERE code='PRD1'"
    ).fetchone()["id"]
    payload = {
        "is_prospect": True,
        "prospect_id": foreign_prospect_id,
        "lignes": [{"produit_id": produit_id, "quantite": 1, "prix_unitaire": 10}],
        "montant_verse": 0,
    }

    foreign_prospect = client.post(
        "/tournee/vente-directe", headers=headers, json=payload
    )
    assert foreign_prospect.status_code == 404

    payload["prospect_id"] = conn.execute(
        "SELECT id FROM prospects_clients WHERE code='PR1'"
    ).fetchone()["id"]
    payload["montant_verse"] = 121
    overpayment = client.post(
        "/tournee/vente-directe", headers=headers, json=payload
    )

    assert overpayment.status_code == 400
    assert conn.execute("SELECT COUNT(*) FROM bons_vente").fetchone()[0] == 0


def test_seller_prospect_endpoints_assign_and_filter_by_authenticated_seller(api_client):
    client, conn = api_client
    headers = _seller_headers(client)
    foreign_id = conn.execute(
        "SELECT id FROM vendeurs WHERE code='V2'"
    ).fetchone()["id"]

    created = client.post(
        "/clients/prospect",
        headers=headers,
        json={"nom": "Prospect Portail", "vendeur_id": foreign_id},
    )

    assert created.status_code == 201
    created_id = created.json()["id"]
    assert conn.execute(
        "SELECT vendeur_id FROM prospects_clients WHERE id=?", (created_id,)
    ).fetchone()["vendeur_id"] == 1

    unassigned_id = conn.execute(
        """INSERT INTO prospects_clients(code, nom, date_creation, statut)
           VALUES ('PR-LEGACY', 'Prospect historique', '2026-11-10', 'Nouveau')"""
    ).lastrowid
    conn.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut)
           VALUES ('PR-FOREIGN', 'Prospect autre vendeur', 2, '2026-11-10', 'Nouveau')"""
    )
    conn.commit()

    listing = client.get("/clients/prospects", headers=headers)
    assert listing.status_code == 200
    prospect_ids = {row["id"] for row in listing.json()}
    assert created_id in prospect_ids
    assert unassigned_id in prospect_ids
    assert not any(row["code"] == "PR-FOREIGN" for row in listing.json())


def test_direct_sale_claims_legacy_unassigned_prospect(api_client):
    client, conn = api_client
    headers = _seller_headers(client)
    produit_id = conn.execute(
        "SELECT id FROM produits WHERE code='PRD1'"
    ).fetchone()["id"]
    prospect_id = conn.execute(
        """INSERT INTO prospects_clients(code, nom, date_creation, statut)
           VALUES ('PR-LEGACY', 'Prospect historique', '2026-11-10', 'Nouveau')"""
    ).lastrowid
    conn.commit()

    response = client.post(
        "/tournee/vente-directe",
        headers=headers,
        json={
            "is_prospect": True,
            "prospect_id": prospect_id,
            "lignes": [{"produit_id": produit_id, "quantite": 1, "prix_unitaire": 10}],
            "montant_verse": 0,
        },
    )

    assert response.status_code == 201
    assert conn.execute(
        "SELECT vendeur_id FROM prospects_clients WHERE id=?", (prospect_id,)
    ).fetchone()["vendeur_id"] == 1
