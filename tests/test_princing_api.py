"""
Test bout en bout : contrôle des prix sur POST /commandes (portail client).
Crée un client CLT-TEST, un produit PRIX-T1 et des commandes de test :
à lancer sur une base jetable, pas sur la vraie base :

    GESTION_STOCK_DB=/tmp/test.db python -m pytest tests
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.db import get_conn, init_db
from api.security import hash_password

client = TestClient(app)


@pytest.fixture
def ctx():
    init_db()
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM clients WHERE code='CLT-TEST'").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO clients (code, nom, tel, solde, password_hash, portail_actif) "
                "VALUES ('CLT-TEST','Client Test API','0600000000',0,?,1)",
                (hash_password("Pass12345"),))
        conn.execute("UPDATE clients SET password_hash=?, portail_actif=1 WHERE code='CLT-TEST'",
                     (hash_password("Pass12345"),))
        cid = conn.execute("SELECT id FROM clients WHERE code='CLT-TEST'").fetchone()[0]
        conn.execute(
            """INSERT INTO produits(code,designation,prix_achat,prix_vente,prix_super_gros,
               prix_gros,prix_detail,prix_special,stock_actuel,actif)
               VALUES('PRIX-T1','Produit test prix',70,120,90,100,120,110,1000,1)
               ON CONFLICT(code) DO UPDATE SET prix_achat=70, prix_vente=120,
               prix_super_gros=90, prix_gros=100, prix_detail=120, prix_special=110,
               prix_moyen_pondere=0, actif=1""")
        pid = conn.execute("SELECT id FROM produits WHERE code='PRIX-T1'").fetchone()[0]
        conn.execute("INSERT INTO clients_niveau_prix(client_id,niveau) VALUES(?, 'gros') "
                     "ON CONFLICT(client_id) DO UPDATE SET niveau='gros'", (cid,))
        conn.commit()
    finally:
        conn.close()
    token = client.post("/auth/login", json={"code_client": "CLT-TEST", "password": "Pass12345"}).json()["access_token"]
    yield {"pid": pid, "headers": {"Authorization": f"Bearer {token}"}}
    conn = get_conn()
    try:
        conn.execute("DELETE FROM clients_niveau_prix WHERE client_id=?", (cid,))
        conn.commit()
    finally:
        conn.close()


def _commande(ctx, prix):
    ligne = {"produit_id": ctx["pid"], "quantite": 1}
    if prix is not None:
        ligne["prix_unitaire"] = prix
    return client.post("/commandes", headers=ctx["headers"], json={"lignes": [ligne]})


def test_catalogue_affiche_le_tarif_du_client(ctx):
    r = client.get("/produits?q=PRIX-T1", headers=ctx["headers"])
    assert r.status_code == 200
    prods = [p for p in r.json() if p["id"] == ctx["pid"]]
    assert prods and prods[0]["prix_unitaire"] == 100  # niveau « gros »


def test_enforce_refuse_un_prix_inferieur_au_tarif(ctx, monkeypatch):
    monkeypatch.setenv("PRIX_CONTROLE_COMMANDES", "enforce")
    r = _commande(ctx, 80)
    assert r.status_code == 409
    assert "Prix non conforme" in r.json()["detail"]


def test_enforce_accepte_le_bon_prix(ctx, monkeypatch):
    monkeypatch.setenv("PRIX_CONTROLE_COMMANDES", "enforce")
    assert _commande(ctx, 100).status_code == 201


def test_warn_par_defaut_ne_bloque_pas(ctx, monkeypatch):
    monkeypatch.delenv("PRIX_CONTROLE_COMMANDES", raising=False)
    assert _commande(ctx, 80).status_code == 201


def test_off_ne_controle_rien(ctx, monkeypatch):
    monkeypatch.setenv("PRIX_CONTROLE_COMMANDES", "off")
    assert _commande(ctx, 80).status_code == 201


def test_ligne_sans_prix_prend_le_tarif_du_client(ctx, monkeypatch):
    monkeypatch.setenv("PRIX_CONTROLE_COMMANDES", "enforce")
    r = _commande(ctx, None)
    assert r.status_code == 201
    assert r.json()["lignes"][0]["prix_unitaire"] == 100  # et non prix_vente (120)
