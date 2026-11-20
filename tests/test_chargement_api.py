import sqlite3
import pytest
from fastapi.testclient import TestClient

from api.deps import get_db
from api.main import app
from api.schema import init_schema
from api.security import hash_password


@pytest.fixture
def api_chargement():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    conn.execute(
        """INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt)
           VALUES ('V1', 'Vendeur 1', 1, ?, 'salt-1')""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO produits(code, designation, actif, stock_actuel, facteur_conversion, prix_achat, prix_vente)
           VALUES ('P1', 'Produit Test', 1, 20, 10, 50, 80)"""
    )
    conn.execute(
        """INSERT INTO produits(code, designation, actif, stock_actuel, facteur_conversion, prix_achat, prix_vente)
           VALUES ('P2', 'Produit Inactif', 0, 100, 10, 50, 80)"""
    )
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    r = client.post("/auth/login-vendeur", json={"code_vendeur": "V1", "password": "Pass12345"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    yield client, conn, headers
    app.dependency_overrides.clear()
    conn.close()


def test_chargement_api_refuse_si_stock_depot_insuffisant(api_chargement):
    client, conn, headers = api_chargement
    # Dépôt = 20 pièces (= 2 colis). On demande 5 colis (= 50 pièces).
    r = client.post(
        "/tournee/chargement",
        json={"lignes": [{"produit_id": 1, "quantite_colis": 5}]},
        headers=headers,
    )
    assert r.status_code == 409
    assert "stock insuffisant" in r.json()["detail"].lower()
    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=1").fetchone()[0] == 20
    assert conn.execute("SELECT COUNT(*) FROM stock_camion_vendeur").fetchone()[0] == 0


def test_chargement_api_refuse_produit_inactif(api_chargement):
    client, conn, headers = api_chargement
    r = client.post(
        "/tournee/chargement",
        json={"lignes": [{"produit_id": 2, "quantite_colis": 1}]},
        headers=headers,
    )
    assert r.status_code == 400
    assert conn.execute("SELECT COUNT(*) FROM bons_chargement").fetchone()[0] == 0


def test_chargement_api_valide_decremente_depot_et_ecrit_journal(api_chargement):
    client, conn, headers = api_chargement
    r = client.post(
        "/tournee/chargement",
        json={"lignes": [{"produit_id": 1, "quantite_colis": 2}]},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=1").fetchone()[0] == 0
    camion = conn.execute("SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE produit_id=1").fetchone()
    assert camion["quantite_colis"] == 2 and camion["quantite_pieces"] == 20
    mvt = conn.execute("SELECT type_mouvement, quantite FROM mouvements_stock WHERE produit_id=1").fetchone()
    assert mvt["type_mouvement"] == "CHARGEMENT_CAMION" and mvt["quantite"] == -20