"""
Priorité 0 / Titre 3 (C1 + C5) : les routes d'administration exigent un utilisateur du
bureau authentifié et autorisé ; les remises vendeur s'écrivent dans `versements_vendeurs`.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import rbac
from api.main import app
from api.rate_limit import _echecs
from api.schema import init_schema
from api.security import hash_password

MDP = "Pass12345"


@pytest.fixture
def api():
    _echecs.clear()
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)  # crée aussi admin/admin123 (doit_changer_mdp = 1)
    for code in ("V1", "V2"):
        conn.execute(
            """INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt)
               VALUES (?, ?, 1, ?, ?)""",
            (code, f"Vendeur {code}", hash_password(MDP), f"salt-{code}"),
        )
    conn.execute(
        "INSERT INTO clients(code, nom, portail_actif, password_hash) VALUES ('C1','Client',1,?)",
        (hash_password(MDP),),
    )
    # V1 a encaissé 1000 en espèces (donc doit 1000 à l'administration)
    conn.execute(
        """INSERT INTO versements_clients(numero, date_vers, client_id, montant, mode, vendeur_id)
           VALUES ('VC1', '2026-11-10', 1, 1000, 'Espèces', 1)"""
    )
    # comptes du bureau, un par rôle (mot de passe déjà changé)
    for username, role in (("boss", "admin"), ("tresor", "caissier"), ("lecteur", "lecture_seule"),
                           ("commercial", "vendeur"), ("gest", "gestionnaire")):
        rbac.creer_utilisateur(conn, username, f"Nom {username}", MDP, role,
                               cree_par="test", doit_changer_mdp=False)
    conn.commit()

    def override_get_db():
        yield conn

    from api.deps import get_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), conn
    app.dependency_overrides.clear()
    conn.close()


def _h(r):
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def admin(client, username="boss"):
    return _h(client.post("/auth/login-admin", json={"username": username, "password": MDP}))


def vendeur(client, code="V1"):
    return _h(client.post("/auth/login-vendeur", json={"code_vendeur": code, "password": MDP}))


def clientp(client):
    return _h(client.post("/auth/login", json={"code_client": "C1", "password": MDP}))


VERS = {"montant": 100}


# ───────────────────────── C1 : un vendeur/client/anonyme n'est pas admin ─────────────────────────

@pytest.mark.parametrize("qui", ["anonyme", "vendeur", "client"])
def test_routes_admin_fermees_aux_non_administrateurs(api, qui):
    client, conn = api
    h = {} if qui == "anonyme" else (vendeur(client) if qui == "vendeur" else clientp(client))
    # même un vendeur qui vise SON PROPRE id est refusé (plus de reçu auto-émis)
    assert client.post("/admin/vendeurs/1/versement", json=VERS, headers=h).status_code == 401
    assert client.post("/admin/vendeurs/2/versement", json=VERS, headers=h).status_code == 401
    assert client.get("/admin/vendeurs/2/dossier", headers=h).status_code == 401
    assert conn.execute("SELECT COUNT(*) FROM versements_vendeurs").fetchone()[0] == 0


def test_jeton_admin_inutilisable_sur_les_routes_vendeur_et_client(api):
    client, _ = api
    h = admin(client)
    assert client.get("/tournee/ma-caisse", headers=h).status_code == 401
    assert client.get("/clients/me", headers=h).status_code == 401


def test_jeton_vendeur_inutilisable_comme_jeton_admin_meme_forge(api):
    client, _ = api
    h = vendeur(client)
    assert client.get("/admin/vendeurs/1/dossier", headers=h).status_code == 401


# ───────────────────────── Connexion admin ─────────────────────────

def test_login_admin_identifiants_faux_et_audit(api):
    client, conn = api
    r = client.post("/auth/login-admin", json={"username": "boss", "password": "faux"})
    assert r.status_code == 401
    assert client.post("/auth/login-admin", json={"username": "inconnu", "password": MDP}).status_code == 401
    echecs = conn.execute("SELECT COUNT(*) FROM journal_audit WHERE action='CONNEXION_ECHEC'").fetchone()[0]
    assert echecs == 2
    admin(client)
    assert conn.execute("SELECT COUNT(*) FROM journal_audit WHERE action='CONNEXION'").fetchone()[0] == 1


def test_compte_par_defaut_admin_admin123_refuse_sur_l_api(api):
    client, _ = api
    r = client.post("/auth/login-admin", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 403
    assert "mot de passe" in r.json()["detail"].lower()


def test_login_admin_limite_les_tentatives(api):
    client, _ = api
    codes = [client.post("/auth/login-admin", json={"username": "boss", "password": "x"}).status_code
             for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_compte_desactive_ou_mot_de_passe_change_invalide_le_jeton(api):
    client, conn = api
    h = admin(client, "gest")
    assert client.get("/admin/vendeurs/1/dossier", headers=h).status_code == 200
    # changement de mot de passe -> jeton révoqué
    uid = conn.execute("SELECT id FROM utilisateurs WHERE username='gest'").fetchone()["id"]
    rbac.changer_mot_de_passe(conn, uid, "NouveauMdp1", doit_changer_mdp=False, modifie_par="test")
    conn.commit()
    assert client.get("/admin/vendeurs/1/dossier", headers=h).status_code == 401
    # désactivation -> jeton révoqué
    h2 = _h(client.post("/auth/login-admin", json={"username": "gest", "password": "NouveauMdp1"}))
    conn.execute("UPDATE utilisateurs SET actif=0 WHERE id=?", (uid,))
    conn.commit()
    assert client.get("/admin/vendeurs/1/dossier", headers=h2).status_code == 401


def test_le_role_est_relu_a_chaque_requete(api):
    client, conn = api
    h = admin(client, "tresor")  # caissier : peut encaisser
    assert client.post("/admin/vendeurs/1/versement", json=VERS, headers=h).status_code == 201
    conn.execute("UPDATE utilisateurs SET role='lecture_seule' WHERE username='tresor'")
    conn.commit()
    assert client.post("/admin/vendeurs/1/versement", json=VERS, headers=h).status_code == 403


# ───────────────────────── Droits par rôle ─────────────────────────

@pytest.mark.parametrize("username,peut_encaisser,peut_voir", [
    ("boss", True, True),
    ("gest", True, True),
    ("tresor", True, False),       # caissier : encaisse, mais pas de pages « équipe »
    ("lecteur", False, True),      # lecture seule : consulte, n'encaisse pas
    ("commercial", False, False),  # rôle vendeur du bureau : ni l'un ni l'autre
])
def test_droits_par_role(api, username, peut_encaisser, peut_voir):
    client, _ = api
    h = admin(client, username)
    assert (client.post("/admin/vendeurs/1/versement", json=VERS, headers=h).status_code == 201) is peut_encaisser
    assert (client.get("/admin/vendeurs/1/dossier", headers=h).status_code == 200) is peut_voir


# ───────────────────────── C5 : bonne table, bonnes règles ─────────────────────────

def test_remise_admin_ecrite_dans_versements_vendeurs_et_deduite_du_reste_a_verser(api):
    client, conn = api
    h = admin(client)
    r = client.post("/admin/vendeurs/1/versement", json={"montant": 400, "observations": "remise lundi"}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["numero"].startswith("VV") and r.json()["vendeur_id"] == 1

    ligne = conn.execute("SELECT * FROM versements_vendeurs").fetchone()
    assert ligne["montant"] == 400 and ligne["cree_par"] == "Nom boss" and ligne["statut"] == "Validé"
    assert conn.execute("SELECT COUNT(*) FROM versements_vendeurs_admin").fetchone()[0] == 0

    hv = vendeur(client)
    assert client.get("/tournee/ma-caisse", headers=hv).json()["reste_a_verser"] == 600
    mes = client.get("/tournee/mes-remises", headers=hv).json()
    assert [m["numero"] for m in mes] == [r.json()["numero"]]
    ancien = client.get("/tournee/versements-admin", headers=hv).json()
    assert [m["numero"] for m in ancien] == [r.json()["numero"]]
    # audité
    assert conn.execute("SELECT COUNT(*) FROM journal_audit WHERE action='VERSEMENT_VENDEUR'").fetchone()[0] == 1


def test_remise_refusee_si_invalide(api):
    client, conn = api
    h = admin(client)
    assert client.post("/admin/vendeurs/1/versement", json={"montant": -5}, headers=h).status_code == 422
    assert client.post("/admin/vendeurs/1/versement", json={"montant": 0}, headers=h).status_code == 422
    assert client.post("/admin/vendeurs/999/versement", json=VERS, headers=h).status_code == 404
    assert client.post("/admin/vendeurs/1/versement", json={"montant": 5000}, headers=h).status_code == 400  # > reste
    assert client.post("/admin/vendeurs/1/versement",
                       json={"montant": 10, "mode": "Chèque"}, headers=h).status_code == 400
    assert conn.execute("SELECT COUNT(*) FROM versements_vendeurs").fetchone()[0] == 0


def test_vendeur_ne_peut_plus_s_emettre_un_recu(api):
    client, conn = api
    hv = vendeur(client)
    r = client.post("/tournee/versement-admin", json={"montant": 999}, headers=hv)
    assert r.status_code == 410
    assert conn.execute("SELECT COUNT(*) FROM versements_vendeurs_admin").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM versements_vendeurs").fetchone()[0] == 0
    assert client.post("/tournee/versement-admin", json={"montant": 1}).status_code in (401, 410)


def test_dossier_admin_repond_et_ne_plante_plus(api):
    client, _ = api
    client.post("/admin/vendeurs/1/versement", json=VERS, headers=admin(client))
    r = client.get("/admin/vendeurs/1/dossier", headers=admin(client))
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"situation", "remises_admin", "stock_camion"}
    assert len(r.json()["remises_admin"]) == 1
    assert client.get("/admin/vendeurs/999/dossier", headers=admin(client)).status_code == 404
