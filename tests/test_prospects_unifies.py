"""
Priorité 0 / Titre 1 : les prospects vivent dans UNE seule table (prospects_clients)
et les routes /clients/prospect* exigent un vendeur authentifié.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schema import init_schema
from api.security import hash_password


@pytest.fixture
def api():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    for code in ("V1", "V2"):
        conn.execute(
            """INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt)
               VALUES (?, ?, 1, ?, ?)""",
            (code, f"Vendeur {code}", hash_password("Pass12345"), f"salt-{code}"),
        )
    conn.commit()

    def override_get_db():
        yield conn

    from api.deps import get_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), conn
    app.dependency_overrides.clear()
    conn.close()


def _headers(client, code):
    r = client.post("/auth/login-vendeur", json={"code_vendeur": code, "password": "Pass12345"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_prospects_refuses_sans_authentification(api):
    client, _ = api
    assert client.get("/clients/prospects").status_code == 401
    assert client.post("/clients/prospect", json={"nom": "Pirate"}).status_code == 401


def test_prospect_cree_dans_prospects_clients_avec_vendeur_de_la_session(api):
    client, conn = api
    h = _headers(client, "V1")
    r = client.post(
        "/clients/prospect",
        json={"nom": "Epicerie Test", "wilaya": "Alger", "vendeur_id": 2},  # vendeur_id forgé
        headers=h,
    )
    assert r.status_code == 201
    row = conn.execute("SELECT * FROM prospects_clients WHERE id=?", (r.json()["id"],)).fetchone()
    assert row["wilaya"] == "Alger"
    vid_v1 = conn.execute("SELECT id FROM vendeurs WHERE code='V1'").fetchone()["id"]
    assert row["vendeur_id"] == vid_v1  # jamais celui du payload
    assert conn.execute("SELECT COUNT(*) FROM prospects_vendeurs").fetchone()[0] == 0


def test_un_vendeur_ne_voit_pas_les_prospects_d_un_autre(api):
    client, _ = api
    client.post("/clients/prospect", json={"nom": "Prospect de V1"}, headers=_headers(client, "V1"))
    noms_v2 = [p["nom"] for p in client.get("/clients/prospects", headers=_headers(client, "V2")).json()]
    assert "Prospect de V1" not in noms_v2


def test_prospect_cree_est_utilisable_en_versement(api):
    client, conn = api
    h = _headers(client, "V1")
    p = client.post("/clients/prospect", json={"nom": "Boutique Z"}, headers=h).json()
    r = client.post(
        "/versements",
        json={"is_prospect": True, "prospect_id": p["id"], "montant": 100, "mode": "Espèces"},
        headers=h,
    )
    assert r.status_code in (200, 201), r.text


def test_aucune_route_dupliquee():
    """Une route déclarée deux fois est masquée en silence (la 1re gagne) : interdit."""
    from api.routers import (
        admin, auth, clients, commandes, factures, produits, tournee, ventes, versements,
    )

    vus = {}
    for module in (admin, auth, clients, commandes, factures, produits, tournee, ventes, versements):
        for route in module.router.routes:
            for methode in getattr(route, "methods", None) or []:
                cle = (methode, route.path)
                assert cle not in vus, f"Route dupliquée : {cle} ({module.__name__})"
                vus[cle] = module.__name__


def test_migration_anciens_prospects_idempotente(api):
    from api.schema import init_schema

    _, conn = api
    conn.execute(
        """INSERT INTO prospects_vendeurs(code, nom, vendeur_id, tel, adresse, ville, solde, date_creation)
           VALUES ('PROSP-001', 'Ancien A', 1, '0550', 'Rue 1', 'Oran', 25.0, '2026-01-05')"""
    )
    # code déjà pris côté prospects_clients -> pas d'écrasement, pas de perte
    conn.execute(
        """INSERT INTO prospects_clients(code, nom, date_creation, statut)
           VALUES ('PROSP-002', 'Déjà là', '2026-01-01', 'Nouveau')"""
    )
    conn.execute(
        """INSERT INTO prospects_vendeurs(code, nom, vendeur_id, date_creation)
           VALUES ('PROSP-002', 'Ancien B', 1, '2026-01-06')"""
    )
    conn.commit()

    init_schema(conn)
    init_schema(conn)  # 2e passage : ne doit rien dupliquer

    rows = {r["nom"]: r for r in conn.execute("SELECT * FROM prospects_clients")}
    assert rows["Ancien A"]["wilaya"] == "Oran" and rows["Ancien A"]["solde"] == 25.0
    assert rows["Ancien A"]["vendeur_id"] == 1
    assert "Ancien B" in rows and rows["Ancien B"]["code"] != "PROSP-002"
    assert rows["Déjà là"]["code"] == "PROSP-002"
    assert conn.execute("SELECT COUNT(*) FROM prospects_clients WHERE nom LIKE 'Ancien%'").fetchone()[0] == 2

    # un prospect migré puis supprimé du bureau ne ressuscite pas
    conn.execute("DELETE FROM prospects_clients WHERE nom='Ancien A'")
    conn.commit()
    init_schema(conn)
    assert conn.execute("SELECT COUNT(*) FROM prospects_clients WHERE nom='Ancien A'").fetchone()[0] == 0


# ─────────── Titre 2 (C6) : une commande ne tombe jamais sur un prospect au hasard ───────────

def _commande(client, headers, **extra):
    corps = {
        "is_prospect": True,
        "lignes": [{"produit_id": 1, "quantite": 1, "prix_unitaire": 10, "total": 10}],
        **extra,
    }
    return client.post("/commandes", json=corps, headers=headers)


@pytest.fixture
def api_cmd(api):
    client, conn = api
    conn.execute(
        """INSERT INTO produits(code, designation, unite, facteur_conversion, prix_vente, stock_actuel, actif)
           VALUES ('P1', 'Produit', 'Pièce', 1, 10, 100, 1)"""
    )
    conn.commit()
    return client, conn


def _nb_commandes_prospects(conn):
    return conn.execute("SELECT COUNT(*) FROM commandes_prospects").fetchone()[0]


def test_commande_prospect_inexistant_refusee_sans_rien_enregistrer(api_cmd):
    client, conn = api_cmd
    h = _headers(client, "V1")
    # un prospect n°1 existe : l'ancien code y aurait rattaché la commande
    client.post("/clients/prospect", json={"nom": "Premier"}, headers=h)

    for extra in ({"prospect_id": 9999}, {"code_client": "PROSP-INCONNU"}, {"nom_client": "Fantôme"}):
        r = _commande(client, h, **extra)
        assert r.status_code == 404, (extra, r.text)
    assert _nb_commandes_prospects(conn) == 0


def test_commande_prospect_ok_par_id_et_par_code(api_cmd):
    client, conn = api_cmd
    h = _headers(client, "V1")
    p = client.post("/clients/prospect", json={"nom": "Boutique A"}, headers=h).json()
    assert _commande(client, h, prospect_id=p["id"]).status_code == 201
    assert _commande(client, h, code_client=p["code"]).status_code == 201
    ids = {r[0] for r in conn.execute("SELECT prospect_id FROM commandes_prospects")}
    assert ids == {p["id"]}


def test_vendeur_ne_peut_pas_commander_sur_le_prospect_d_un_autre(api_cmd):
    client, conn = api_cmd
    p_v1 = client.post("/clients/prospect", json={"nom": "Chez V1"}, headers=_headers(client, "V1")).json()
    h2 = _headers(client, "V2")
    for extra in ({"prospect_id": p_v1["id"]}, {"code_client": p_v1["code"]}, {"nom_client": "Chez V1"}):
        assert _commande(client, h2, **extra).status_code == 404, extra
    assert _nb_commandes_prospects(conn) == 0


def test_nom_homonyme_ambigu_refuse(api_cmd):
    client, conn = api_cmd
    h = _headers(client, "V1")
    client.post("/clients/prospect", json={"nom": "Epicerie Centrale"}, headers=h)
    client.post("/clients/prospect", json={"nom": "Epicerie Centrale"}, headers=h)
    assert _commande(client, h, nom_client="Epicerie Centrale").status_code == 404
    assert _nb_commandes_prospects(conn) == 0
