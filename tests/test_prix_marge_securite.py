import sqlite3
import pytest
from fastapi.testclient import TestClient

from api.deps import get_db
from api.main import app
from api.schema import init_schema
from api.security import hash_password


@pytest.fixture
def api_prix():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    conn.execute(
        "INSERT INTO clients(code, nom, portail_actif, password_hash) VALUES ('C1', 'Client 1', 1, ?)",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt)
           VALUES ('V1', 'Vendeur 1', 1, ?, 'salt-1')""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO produits(code, designation, facteur_conversion, prix_achat, prix_vente, stock_actuel, actif)
           VALUES ('P1', 'Glace 12', 12, 80, 100, 100, 1)"""
    )
    conn.execute(
        """INSERT INTO stock_camion_vendeur(vendeur_id, produit_id, quantite_colis, quantite_pieces)
           VALUES (1, 1, 5, 60)"""
    )
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    hc = {"Authorization": f"Bearer {client.post('/auth/login', json={'code_client': 'C1', 'password': 'Pass12345'}).json()['access_token']}"}
    hv = {"Authorization": f"Bearer {client.post('/auth/login-vendeur', json={'code_vendeur': 'V1', 'password': 'Pass12345'}).json()['access_token']}"}
    yield client, hc, hv
    app.dependency_overrides.clear()
    conn.close()


def test_commande_ignore_total_et_montant_falsifies(api_prix):
    client, hc, _ = api_prix
    # 2 colis * 12 pcs * 100 DA = 2400 DA, même si le client envoie total=1 et montant_total=1
    r = client.post(
        "/commandes",
        headers=hc,
        json={
            "montant_total": 1,
            "lignes": [{"produit_id": 1, "quantite": 2, "prix_unitaire": 100, "total": 1}],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["lignes"][0]["total"] == 2400
    assert r.json()["montant_total"] == 2400


def test_vente_directe_refuse_vente_a_perte_en_mode_enforce(api_prix, monkeypatch):
    client, _, hv = api_prix
    monkeypatch.setenv("PRIX_CONTROLE_COMMANDES", "enforce")
    r = client.post(
        "/tournee/vente-directe",
        headers=hv,
        json={
            "code_client": "C1",
            "lignes": [{"produit_id": 1, "quantite": 1, "prix_unitaire": 50}],  # < prix_achat (80)
            "montant_verse": 0,
        },
    )
    assert r.status_code == 409