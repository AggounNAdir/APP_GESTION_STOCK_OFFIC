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

    # Produits : actif, inactif, supprimé
    conn.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion, prix_vente, stock_actuel, actif, supprime)
           VALUES ('P-ACTIF', 'Produit Actif', 'Colis', 1, 100.0, 10.0, 1, 0)"""
    )
    conn.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion, prix_vente, stock_actuel, actif, supprime)
           VALUES ('P-INACTIF', 'Produit Inactif', 'Colis', 1, 100.0, 10.0, 0, 0)"""
    )
    conn.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion, prix_vente, stock_actuel, actif, supprime)
           VALUES ('P-SUPPR', 'Produit Supprime', 'Colis', 1, 100.0, 10.0, 1, 1)"""
    )

    # Client officiel + COMPTOIR
    conn.execute(
        """INSERT INTO clients (code, nom, tel, solde, portail_actif, password_hash)
           VALUES ('C1', 'Client Un', '0555111111', 1000.0, 1, ?)""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO clients (code, nom, tel, solde, portail_actif)
           VALUES ('COMPTOIR', 'Client Comptoir', '0500000000', 0.0, 0)"""
    )

    # Vendeur + Prospect
    conn.execute(
        """INSERT INTO vendeurs (code, nom, actif, password_hash, session_salt)
           VALUES ('V1', 'Vendeur Un', 1, ?, 'salt-m3-m4')""",
        (hash_password("Pass12345"),),
    )
    conn.execute(
        """INSERT INTO prospects_clients (code, nom, tel, vendeur_id, solde, date_creation, statut)
           VALUES ('PR1', 'Prospect Un', '0777777777', 1, 300.0, '2026-11-10', 'Nouveau')"""
    )

    c1_id = conn.execute("SELECT id FROM clients WHERE code='C1'").fetchone()["id"]
    comptoir_id = conn.execute("SELECT id FROM clients WHERE code='COMPTOIR'").fetchone()["id"]
    pr1_id = conn.execute("SELECT id FROM prospects_clients WHERE code='PR1'").fetchone()["id"]

    # Bons client C1 : 1 validé + 1 annulé
    conn.execute(
        """INSERT INTO bons_vente (numero, date_bon, client_id, prospect_id, vendeur_id, total, montant_verse, statut)
           VALUES ('BV-VALIDE', '2026-11-10', ?, NULL, 1, 1000.0, 0.0, 'Validé')""",
        (c1_id,),
    )
    conn.execute(
        """INSERT INTO bons_vente (numero, date_bon, client_id, prospect_id, vendeur_id, total, montant_verse, statut)
           VALUES ('BV-ANNULE', '2026-11-11', ?, NULL, 1, 9999.0, 0.0, 'Annulé')""",
        (c1_id,),
    )

    # Ventes vendeur V1 sur prospect PR1 (client_id = COMPTOIR) : 1 validé + 1 annulé
    conn.execute(
        """INSERT INTO bons_vente (numero, date_bon, client_id, prospect_id, vendeur_id, total, montant_verse, statut)
           VALUES ('BV-PROSP-OK', '2026-11-12', ?, ?, 1, 500.0, 200.0, 'Validé')""",
        (comptoir_id, pr1_id),
    )
    conn.execute(
        """INSERT INTO bons_vente (numero, date_bon, client_id, prospect_id, vendeur_id, total, montant_verse, statut)
           VALUES ('BV-PROSP-ANN', '2026-11-12', ?, ?, 1, 8888.0, 8888.0, 'Annulé')""",
        (comptoir_id, pr1_id),
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


def test_catalogue_exclut_produits_inactifs_et_supprimes(api_client):
    client, _ = api_client
    login = client.post("/auth/login", json={"code_client": "C1", "password": "Pass12345"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res_all = client.get("/produits", headers=headers)
    assert res_all.status_code == 200
    codes_all = [p["code"] for p in res_all.json()]
    assert "P-ACTIF" in codes_all
    assert "P-INACTIF" not in codes_all
    assert "P-SUPPR" not in codes_all

    res_q = client.get("/produits?q=Produit", headers=headers)
    assert res_q.status_code == 200
    codes_q = [p["code"] for p in res_q.json()]
    assert codes_q == ["P-ACTIF"]


def test_bons_annules_exclus_du_releve_et_historique_client(api_client):
    client, conn = api_client
    login = client.post("/auth/login", json={"code_client": "C1", "password": "Pass12345"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    annule_id = conn.execute(
        "SELECT id FROM bons_vente WHERE numero='BV-ANNULE'"
    ).fetchone()["id"]

    # /clients/me/ventes
    me_ventes = client.get("/clients/me/ventes", headers=headers)
    assert me_ventes.status_code == 200
    assert [b["numero"] for b in me_ventes.json()] == ["BV-VALIDE"]

    # /ventes et /ventes/{id}
    ventes = client.get("/ventes", headers=headers)
    assert ventes.status_code == 200
    assert [b["numero"] for b in ventes.json()] == ["BV-VALIDE"]
    assert client.get(f"/ventes/{annule_id}", headers=headers).status_code == 404

    # /clients/me/situation
    sit = client.get("/clients/me/situation", headers=headers)
    assert sit.status_code == 200
    data = sit.json()
    assert data["total_debit"] == 1000.0
    assert [l["numero"] for l in data["lignes"]] == ["BV-VALIDE"]


def test_admin_ventes_vendeurs_et_situation_journaliere_m4(api_client):
    client, _ = api_client
    login = client.post(
        "/auth/login-vendeur",
        json={"code_vendeur": "V1", "password": "Pass12345"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    ventes = client.get("/admin/ventes-vendeurs?date_jour=2026-11-12", headers=headers)
    assert ventes.status_code == 200
    rows = ventes.json()
    assert len(rows) == 1
    assert rows[0]["numero"] == "BV-PROSP-OK"
    assert rows[0]["code_client"] == "PR1"
    assert rows[0]["tel"] == "0777777777"

    sit = client.get(
        "/admin/situation-journaliere-vendeurs?date_jour=2026-11-12",
        headers=headers,
    )
    assert sit.status_code == 200
    s = sit.json()[0]
    assert s["nb_ventes"] == 1
    assert s["ca_total"] == 500.0
    assert s["total_encaisse"] == 200.0
    assert s["reste_credit"] == 300.0

    # Jour sans vente : valeurs à 0 (et non None)
    sit_vide = client.get(
        "/admin/situation-journaliere-vendeurs?date_jour=2026-01-01",
        headers=headers,
    )
    assert sit_vide.status_code == 200
    sv = sit_vide.json()[0]
    assert sv["nb_ventes"] == 0
    assert sv["ca_total"] == 0.0