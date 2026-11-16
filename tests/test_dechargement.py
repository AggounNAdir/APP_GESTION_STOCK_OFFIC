import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import dechargement_service as dch
from api import vendeur_dossier
from api.chargement_service import creer_bon_chargement, decharger_camion
from api.deps import get_db
from api.main import app
from api.schema import init_schema
from api.security import hash_password
from api.stock_journal import reprise_stock_existant


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    for code, nom in (("V1", "Vendeur Un"), ("V2", "Vendeur Deux")):
        c.execute(
            "INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt) VALUES(?,?,1,?,?)",
            (code, nom, hash_password("Pass12345"), f"salt-{code}"),
        )
    c.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion, prix_achat,
                                 prix_vente, stock_actuel, actif)
           VALUES ('P1', 'Produit Un', 'Carton', 12, 5, 10, 120, 1)"""
    )
    c.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion, prix_achat,
                                 prix_vente, stock_actuel, actif)
           VALUES ('P2', 'Produit Deux', 'Carton', 6, 20, 30, 60, 1)"""
    )
    reprise_stock_existant(c)
    c.commit()
    yield c
    c.close()


def _ids(c):
    v1 = c.execute("SELECT id FROM vendeurs WHERE code='V1'").fetchone()[0]
    v2 = c.execute("SELECT id FROM vendeurs WHERE code='V2'").fetchone()[0]
    p1 = c.execute("SELECT id FROM produits WHERE code='P1'").fetchone()[0]
    p2 = c.execute("SELECT id FROM produits WHERE code='P2'").fetchone()[0]
    return v1, v2, p1, p2


def _stock(c, table, where, params):
    return c.execute(f"SELECT {table} FROM {where}", params).fetchone()[0]


def _depot(c, pid):
    return c.execute("SELECT stock_actuel FROM produits WHERE id=?", (pid,)).fetchone()[0]


def _camion(c, vid, pid):
    r = c.execute(
        "SELECT quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?", (vid, pid)
    ).fetchone()
    return r[0] if r else None


def _charge(c):
    v1, v2, p1, p2 = _ids(c)
    creer_bon_chargement(c, v1, [(p1, 5), (p2, 4)])  # 60 + 24 pièces ; dépôt : 60 et 36
    return v1, v2, p1, p2


# ─────────────────────────── service ───────────────────────────

def test_demande_ne_touche_ni_depot_ni_camion(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])

    assert bon["statut"] == "En attente" and bon["numero"].startswith("DCH-")
    assert bon["total_theorique_pieces"] == 84 and bon["total_ecart_pieces"] == 0
    assert _depot(conn, p1) == 60 and _camion(conn, v1, p1) == 60


def test_validation_reintegre_le_rendu_et_vide_le_camion(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])

    dch.valider_dechargement(conn, bon["id"], "Admin")

    assert _depot(conn, p1) == 120 and _depot(conn, p2) == 60
    assert _camion(conn, v1, p1) == 0 and _camion(conn, v1, p2) == 0
    mv = conn.execute(
        "SELECT quantite, document_numero, tiers_nom, utilisateur FROM mouvements_stock "
        "WHERE type_mouvement='RETOUR_CAMION' AND document_id=? ORDER BY produit_id", (bon["id"],)
    ).fetchall()
    assert [m["quantite"] for m in mv] == [60, 24]
    assert mv[0]["document_numero"] == bon["numero"] and mv[0]["tiers_nom"] == "Vendeur Un"
    assert dch.detail_dechargement(conn, bon["id"])["decide_par"] == "Admin"


def test_ecart_manquant_est_valorise_et_retire_du_camion(conn):
    v1, _, p1, p2 = _charge(conn)
    # P1 : 4 colis rendus sur 5 -> 12 pièces manquantes (5 DA) ; P2 : tout rendu
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 4, "MANQUANT"), (p2, 4)])
    assert bon["total_ecart_pieces"] == 12 and bon["valeur_ecart"] == 60

    dch.valider_dechargement(conn, bon["id"], "Admin")

    assert _depot(conn, p1) == 60 + 48          # seul le rendu réintègre le dépôt
    assert _camion(conn, v1, p1) == 0           # l'écart ne reste pas dans le camion
    s = vendeur_dossier.situation_vendeur(conn, v1)
    assert s["ecart_dechargement_pieces"] == 12 and s["ecart_dechargement_valeur"] == 60
    assert s["dechargements_en_attente"] == 0


def test_motif_garde_conserve_le_stock_dans_le_camion_sans_ecart(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 3, "GARDE"), (p2, 4)])
    assert bon["total_ecart_pieces"] == 0 and bon["valeur_ecart"] == 0

    dch.valider_dechargement(conn, bon["id"], "Admin")

    assert _camion(conn, v1, p1) == 24          # 2 colis gardés
    assert conn.execute(
        "SELECT quantite_colis FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?", (v1, p1)
    ).fetchone()[0] == 2
    assert _depot(conn, p1) == 60 + 36


def test_rendu_zero_avec_motif_ne_cree_aucun_mouvement_pour_ce_produit(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 0, "CASSE"), (p2, 4)])
    dch.valider_dechargement(conn, bon["id"], "Admin")

    assert _depot(conn, p1) == 60
    assert conn.execute(
        "SELECT COUNT(*) FROM mouvements_stock WHERE type_mouvement='RETOUR_CAMION' AND produit_id=?", (p1,)
    ).fetchone()[0] == 0


@pytest.mark.parametrize("lignes, message", [
    ([(1, 6, None), (2, 4, None)], "n'en contient"),                 # plus que le camion
    ([(1, 4, None), (2, 4, None)], "indiquez le motif"),             # écart sans motif
    ([(1, 5, None)], "Saisissez la quantité rendue"),                # produit oublié
    ([(1, 5, "BIDON"), (2, 4, None)], "Motif d'écart inconnu"),
    ([(1, -1, None), (2, 4, None)], "positif ou nul"),
    ([(1, 5, None), (1, 5, None), (2, 4, None)], "qu'une seule fois"),
    ([(99, 1, None), (1, 5, None), (2, 4, None)], "absent du camion"),
])
def test_demande_refusee_sans_rien_creer(conn, lignes, message):
    v1, _, p1, p2 = _charge(conn)
    assert (p1, p2) == (1, 2)
    with pytest.raises(ValueError, match=message):
        dch.creer_demande_dechargement(conn, v1, lignes)
    assert conn.execute("SELECT COUNT(*) FROM bons_dechargement").fetchone()[0] == 0


def test_compteur_global_des_demandes_en_attente(conn):
    v1, v2, p1, p2 = _charge(conn)
    assert dch.compter_en_attente(conn) == 0
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])
    assert dch.compter_en_attente(conn) == 1
    assert vendeur_dossier.situation_vendeur(conn, v1)["dechargements_en_attente"] == 1
    assert vendeur_dossier.situation_vendeur(conn, v2)["dechargements_en_attente"] == 0
    dch.rejeter_dechargement(conn, bon["id"], "Admin", "Recompter")
    assert dch.compter_en_attente(conn) == 0


def test_camion_vide_refuse(conn):
    v1, *_ = _ids(conn)
    with pytest.raises(ValueError, match="déjà vide"):
        dch.creer_demande_dechargement(conn, v1, [(1, 1)])


def test_une_seule_demande_en_attente_et_camion_fige(conn):
    v1, _, p1, p2 = _charge(conn)
    dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])

    with pytest.raises(ValueError, match="en attente de validation"):
        dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])
    with pytest.raises(ValueError, match="en attente de validation"):
        creer_bon_chargement(conn, v1, [(p1, 1)])
    with pytest.raises(ValueError, match="en attente de validation"):
        decharger_camion(conn, v1)


def test_validation_refusee_si_le_camion_a_change(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])
    conn.execute("UPDATE stock_camion_vendeur SET quantite_pieces=48 WHERE vendeur_id=? AND produit_id=?", (v1, p1))
    conn.commit()

    with pytest.raises(ValueError, match="a changé depuis la demande"):
        dch.valider_dechargement(conn, bon["id"], "Admin")
    assert _depot(conn, p1) == 60 and dch.detail_dechargement(conn, bon["id"])["statut"] == "En attente"


def test_rejet_exige_un_motif_et_laisse_tout_intact(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])

    with pytest.raises(ValueError, match="motif du rejet"):
        dch.rejeter_dechargement(conn, bon["id"], "Admin", "  ")
    r = dch.rejeter_dechargement(conn, bon["id"], "Admin", "Recompter")

    assert r["statut"] == "Rejeté" and r["motif_rejet"] == "Recompter"
    assert _depot(conn, p1) == 60 and _camion(conn, v1, p1) == 60
    assert dch.dechargement_en_attente(conn, v1) is None
    creer_bon_chargement(conn, v1, [(p1, 1)])    # le camion est de nouveau utilisable


def test_decision_definitive_et_pas_de_double_validation(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])
    dch.valider_dechargement(conn, bon["id"], "Admin")

    for fn in (lambda: dch.valider_dechargement(conn, bon["id"], "Admin"),
               lambda: dch.rejeter_dechargement(conn, bon["id"], "Admin", "x"),
               lambda: dch.annuler_demande_dechargement(conn, bon["id"], v1)):
        with pytest.raises(ValueError, match="déjà « Validé »"):
            fn()
    assert _depot(conn, p1) == 120      # un seul retour en stock


def test_annulation_par_le_vendeur_seulement_pour_sa_demande(conn):
    v1, v2, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 5), (p2, 4)])

    with pytest.raises(ValueError, match="introuvable"):
        dch.annuler_demande_dechargement(conn, bon["id"], v2)
    assert dch.annuler_demande_dechargement(conn, bon["id"], v1)["statut"] == "Annulé"


def test_arrondis_colis_fractionnaires(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 4.5, "CASSE"), (p2, 4)])
    assert bon["lignes"][1]["ecart_pieces"] == 6 and bon["lignes"][1]["ecart_colis"] == 0.5


# ─────────────────────────── API ───────────────────────────

@pytest.fixture
def api(conn):
    app.dependency_overrides[get_db] = lambda: (yield conn)
    yield TestClient(app), conn
    app.dependency_overrides.clear()


def _headers(client, code="V1"):
    r = client.post("/auth/login-vendeur", json={"code_vendeur": code, "password": "Pass12345"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_api_flux_demande_puis_validation_admin(api):
    client, conn = api
    v1, _, p1, p2 = _charge(conn)
    h = _headers(client)

    r = client.post("/tournee/dechargement/demande", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 4, "motif_ecart": "MANQUANT"},
                   {"produit_id": p2, "quantite_colis": 4}],
        "observations": "fin de journée"})
    assert r.status_code == 201, r.text
    bon = r.json()
    assert bon["statut"] == "En attente" and bon["total_ecart_pieces"] == 12

    # camion figé : vente et chargement refusés (409)
    assert client.post("/tournee/chargement", headers=h,
                       json={"lignes": [{"produit_id": p1, "quantite_colis": 1}]}).status_code == 409
    assert client.post("/tournee/vente-directe", headers=h, json={
        "nom_client": "X", "lignes": [{"produit_id": p1, "quantite": 1, "prix_unitaire": 10}]}).status_code == 409
    assert client.post("/tournee/dechargement/demande", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 4}]}).status_code == 409

    lst = client.get("/tournee/dechargements", headers=h).json()
    assert [b["numero"] for b in lst] == [bon["numero"]]

    dch.valider_dechargement(conn, bon["id"], "Admin")      # côté administration (application bureau)
    assert client.get(f"/tournee/dechargements/{bon['id']}", headers=h).json()["statut"] == "Validé"
    assert _depot(conn, p1) == 108


def test_api_annulation_debloque_le_camion(api):
    client, conn = api
    v1, _, p1, p2 = _charge(conn)
    h = _headers(client)
    bon = client.post("/tournee/dechargement/demande", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 5}, {"produit_id": p2, "quantite_colis": 4}]}).json()

    assert client.post(f"/tournee/dechargements/{bon['id']}/annuler", headers=h).json()["statut"] == "Annulé"
    assert client.post("/tournee/chargement", headers=h,
                       json={"lignes": [{"produit_id": p1, "quantite_colis": 1}]}).status_code == 201


def test_api_isolation_entre_vendeurs(api):
    client, conn = api
    v1, v2, p1, p2 = _charge(conn)
    bon = client.post("/tournee/dechargement/demande", headers=_headers(client), json={
        "lignes": [{"produit_id": p1, "quantite_colis": 5}, {"produit_id": p2, "quantite_colis": 4}]}).json()
    h2 = _headers(client, "V2")

    assert client.get("/tournee/dechargements", headers=h2).json() == []
    assert client.get(f"/tournee/dechargements/{bon['id']}", headers=h2).status_code == 404
    assert client.post(f"/tournee/dechargements/{bon['id']}/annuler", headers=h2).status_code == 400


def test_api_validations_et_ancienne_route(api):
    client, conn = api
    v1, _, p1, p2 = _charge(conn)
    h = _headers(client)

    assert client.post("/tournee/dechargement", headers=h).status_code == 410
    assert client.post("/tournee/dechargement/demande", json={"lignes": []}).status_code in (401, 403)
    assert client.post("/tournee/dechargement/demande", headers=h, json={"lignes": []}).status_code == 422
    assert client.post("/tournee/dechargement/demande", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 99}, {"produit_id": p2, "quantite_colis": 4}]}).status_code == 400
    assert _depot(conn, p1) == 60 and conn.execute("SELECT COUNT(*) FROM bons_dechargement").fetchone()[0] == 0


# ─────────────────────────── casse rapportée ───────────────────────────

def test_carton_casse_ne_reintegre_pas_le_stock_vendable(conn):
    """Cas réel : 1 carton cassé rapporté ne doit pas remonter le stock du dépôt de 50 pièces."""
    v1, _, p1, p2 = _charge(conn)
    # P1 : camion 5 colis ; 4 rendus bon état + 1 cassé. P2 : tout rendu bon état.
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 4, None, 1), (p2, 4)])
    assert bon["total_casse_pieces"] == 12 and bon["valeur_casse"] == 60
    assert bon["total_ecart_pieces"] == 0                      # la casse n'est pas un écart

    dch.valider_dechargement(conn, bon["id"], "Admin")

    assert _depot(conn, p1) == 60 + 48                         # seulement les 4 colis en bon état
    assert _camion(conn, v1, p1) == 0                          # le camion est bien vidé
    mv = conn.execute(
        "SELECT type_mouvement, quantite, stock_avant, stock_apres FROM mouvements_stock "
        "WHERE document_type='bon_dechargement' AND document_id=? AND produit_id=? ORDER BY id", (bon["id"], p1)
    ).fetchall()
    assert [(m["type_mouvement"], m["quantite"]) for m in mv] == [("RETOUR_CAMION", 60), ("CASSE_CAMION", -12)]
    assert mv[0]["stock_apres"] == mv[1]["stock_avant"] == 120  # chaîne du journal cohérente
    assert mv[1]["stock_apres"] == 108
    assert vendeur_dossier.situation_vendeur(conn, v1)["casse_dechargement_valeur"] == 60


def test_tout_casse_laisse_le_depot_inchange(conn):
    v1, _, p1, p2 = _charge(conn)
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 0, None, 5), (p2, 4)])
    dch.valider_dechargement(conn, bon["id"], "Admin")
    assert _depot(conn, p1) == 60 and _camion(conn, v1, p1) == 0


def test_casse_et_manquant_et_garde_se_combinent(conn):
    v1, _, p1, p2 = _charge(conn)
    # P1 (5 colis) : 2 bon état + 1 cassé + 1 manquant + 1 gardé -> écart = 2 (manquant + gardé), motif requis
    with pytest.raises(ValueError, match="indiquez le motif"):
        dch.creer_demande_dechargement(conn, v1, [(p1, 2, None, 1), (p2, 4)])
    bon = dch.creer_demande_dechargement(conn, v1, [(p1, 2, "MANQUANT", 1), (p2, 4)])
    assert bon["total_casse_pieces"] == 12 and bon["total_ecart_pieces"] == 24
    dch.valider_dechargement(conn, bon["id"], "Admin")
    assert _depot(conn, p1) == 60 + 24 and _camion(conn, v1, p1) == 0


def test_bon_etat_plus_casse_ne_peut_depasser_le_camion(conn):
    v1, _, p1, p2 = _charge(conn)
    with pytest.raises(ValueError, match="bon état \\+ cassés"):
        dch.creer_demande_dechargement(conn, v1, [(p1, 4, None, 2), (p2, 4)])
    with pytest.raises(ValueError, match="positif ou nul"):
        dch.creer_demande_dechargement(conn, v1, [(p1, 5, None, -1), (p2, 4)])
    assert conn.execute("SELECT COUNT(*) FROM bons_dechargement").fetchone()[0] == 0


def test_api_casse_dans_la_demande(api):
    client, conn = api
    v1, _, p1, p2 = _charge(conn)
    r = client.post("/tournee/dechargement/demande", headers=_headers(client), json={"lignes": [
        {"produit_id": p1, "quantite_colis": 4, "quantite_casse_colis": 1},
        {"produit_id": p2, "quantite_colis": 4}]})
    assert r.status_code == 201, r.text
    bon = r.json()
    assert bon["total_casse_pieces"] == 12
    assert {l["produit_id"]: l["casse_colis"] for l in bon["lignes"]} == {p1: 1, p2: 0}


def test_migration_base_existante_sans_colonnes_casse():
    """Une base créée avec la première version (sans casse) doit être mise à niveau sans perte."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_schema(c)
    c.executescript("""
        DROP TABLE lignes_dechargement; DROP TABLE bons_dechargement;
        CREATE TABLE bons_dechargement (id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT UNIQUE NOT NULL,
            date_demande TEXT NOT NULL, vendeur_id INTEGER NOT NULL, statut TEXT DEFAULT 'En attente',
            total_theorique_pieces REAL DEFAULT 0, total_reel_pieces REAL DEFAULT 0,
            total_ecart_pieces REAL DEFAULT 0, valeur_ecart REAL DEFAULT 0, observations TEXT,
            date_decision TEXT, decide_par TEXT, motif_rejet TEXT);
        CREATE TABLE lignes_dechargement (id INTEGER PRIMARY KEY AUTOINCREMENT, dechargement_id INTEGER NOT NULL,
            produit_id INTEGER NOT NULL, facteur REAL DEFAULT 1, theorique_pieces REAL NOT NULL,
            reel_pieces REAL NOT NULL, ecart_pieces REAL NOT NULL DEFAULT 0, motif_ecart TEXT, prix_unitaire REAL DEFAULT 0);
        INSERT INTO vendeurs(code, nom, actif) VALUES('V9','Ancien',1);
        INSERT INTO bons_dechargement(numero, date_demande, vendeur_id) VALUES('DCH-OLD', '2026-11-01', 1);
    """)
    init_schema(c)
    cols_bon = [r[1] for r in c.execute("PRAGMA table_info(bons_dechargement)")]
    cols_lig = [r[1] for r in c.execute("PRAGMA table_info(lignes_dechargement)")]
    assert {"total_casse_pieces", "valeur_casse"} <= set(cols_bon) and "casse_pieces" in cols_lig
    old = c.execute("SELECT numero, total_casse_pieces FROM bons_dechargement").fetchone()
    assert tuple(old) == ("DCH-OLD", 0)
    c.close()
