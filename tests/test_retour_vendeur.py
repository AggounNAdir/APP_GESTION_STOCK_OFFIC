import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import retour_vendeur_service as rtv
from api import vendeur_dossier
from api.chargement_service import creer_bon_chargement
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
        c.execute("INSERT INTO vendeurs(code, nom, actif, password_hash, session_salt) VALUES(?,?,1,?,?)",
                  (code, nom, hash_password("Pass12345"), f"salt-{code}"))
    # P1 : carton de 50 pièces, achat 5, vente 10
    c.execute("""INSERT INTO produits (code, designation, unite, facteur_conversion, prix_achat, prix_vente, stock_actuel, actif)
                 VALUES ('P1', 'Produit Un', 'Carton', 50, 5, 10, 500, 1)""")
    c.execute("""INSERT INTO produits (code, designation, unite, facteur_conversion, prix_achat, prix_vente, stock_actuel, actif)
                 VALUES ('P2', 'Produit Deux', 'Carton', 6, 20, 30, 60, 1)""")
    reprise_stock_existant(c)
    c.commit()
    yield c
    c.close()


def ids(c):
    g = lambda sql: c.execute(sql).fetchone()[0]
    return (g("SELECT id FROM vendeurs WHERE code='V1'"), g("SELECT id FROM vendeurs WHERE code='V2'"),
            g("SELECT id FROM produits WHERE code='P1'"), g("SELECT id FROM produits WHERE code='P2'"))


def camion(c, v, p):
    r = c.execute("SELECT quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?", (v, p)).fetchone()
    return r[0] if r else None


def depot(c, p):
    return c.execute("SELECT stock_actuel FROM produits WHERE id=?", (p,)).fetchone()[0]


def tampon(c, p):
    return c.execute("SELECT stock_retours_pieces FROM produits WHERE id=?", (p,)).fetchone()[0]


def charge(c):
    v1, v2, p1, p2 = ids(c)
    creer_bon_chargement(c, v1, [(p1, 5), (p2, 4)])   # 250 + 24 pièces dans le camion
    return v1, v2, p1, p2


# ───────────── le cas décrit : 1 carton retourné = 50 pièces ─────────────

def test_un_carton_retourne_baisse_le_camion_de_50_pieces_apres_confirmation(conn):
    v1, _, p1, p2 = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU")], retourne_par="Karim (chauffeur)")

    assert r["statut"] == "En attente" and r["numero"].startswith("RTV-") and r["retourne_par"] == "Karim (chauffeur)"
    assert camion(conn, v1, p1) == 250 and tampon(conn, p1) in (0, None)   # rien ne bouge avant confirmation

    rtv.confirmer_retour(conn, r["id"], "Admin")

    assert camion(conn, v1, p1) == 200                    # -1 carton (50 pcs)
    assert conn.execute("SELECT quantite_colis FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
                        (v1, p1)).fetchone()[0] == 4
    assert tampon(conn, p1) == 50                         # zone « retours à traiter »
    assert depot(conn, p1) == 250                         # pas encore vendable (500 - 250 chargés)
    s = vendeur_dossier.situation_vendeur(conn, v1)
    assert s["retours_colis"] == 1 and s["retours_valeur"] == 500      # 50 pcs x prix de vente 10
    assert s["retours_en_attente"] == 0


def test_retourne_par_par_defaut_le_vendeur(conn):
    v1, _, p1, _ = charge(conn)
    assert rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU")])["retourne_par"] == "Vendeur Un"


# ───────────── décision sur chaque produit retourné ─────────────

def _confirme(conn, lignes):
    v1, _, p1, p2 = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1 if k == "p1" else p2, q, m, *c) for k, q, m, *c in lignes])
    return v1, p1, p2, rtv.confirmer_retour(conn, r["id"], "Admin")


def test_vendable_reintegre_le_stock_et_vide_la_zone_retours(conn):
    v1, p1, p2, r = _confirme(conn, [("p1", 1, "INVENDU")])
    rtv.decider_ligne(conn, r["lignes"][0]["id"], "VENDABLE", "Admin")
    assert depot(conn, p1) == 300 and tampon(conn, p1) == 0
    mv = conn.execute("SELECT type_mouvement, quantite, tiers_nom FROM mouvements_stock "
                      "WHERE document_type='retour_vendeur' AND produit_id=?", (p1,)).fetchall()
    assert [(m["type_mouvement"], m["quantite"]) for m in mv] == [("RETOUR_CAMION", 50)]
    assert mv[0]["tiers_nom"] == "Vendeur Un"


@pytest.mark.parametrize("imputation, cle", [("VENDEUR", "casse_mois_vendeur_valeur"),
                                             ("ENTREPRISE", "casse_mois_entreprise_valeur")])
def test_casse_ne_reintegre_pas_et_est_imputee(conn, imputation, cle):
    v1, p1, p2, r = _confirme(conn, [("p1", 1, "CASSE")])
    with pytest.raises(ValueError, match="imputée au vendeur ou à l'entreprise"):
        rtv.decider_ligne(conn, r["lignes"][0]["id"], "CASSE", "Admin")
    res = rtv.decider_ligne(conn, r["lignes"][0]["id"], "CASSE", "Admin", imputation)

    assert res["valeur_perte"] == 250                     # 50 pcs x prix d'achat 5
    assert depot(conn, p1) == 250 and tampon(conn, p1) == 0
    mv = conn.execute("SELECT type_mouvement, quantite, stock_avant, stock_apres FROM mouvements_stock "
                      "WHERE document_type='retour_vendeur' AND produit_id=? ORDER BY id", (p1,)).fetchall()
    assert [(m["type_mouvement"], m["quantite"]) for m in mv] == [("RETOUR_CAMION", 50), ("CASSE_CAMION", -50)]
    assert mv[0]["stock_apres"] == mv[1]["stock_avant"] and mv[1]["stock_apres"] == 250
    assert rtv.situation_depot(conn)[cle] == 250
    s = vendeur_dossier.situation_vendeur(conn, v1)
    assert s["casse_imputee_valeur"] == (250 if imputation == "VENDEUR" else 0)


def test_fournisseur_sort_du_stock_vendable(conn):
    v1, p1, p2, r = _confirme(conn, [("p1", 1, "PERIME")])
    rtv.decider_ligne(conn, r["lignes"][0]["id"], "FOURNISSEUR", "Admin")
    assert depot(conn, p1) == 250 and tampon(conn, p1) == 0
    assert rtv.situation_depot(conn)["a_retourner_fournisseur_valeur"] == 250
    assert conn.execute("SELECT type_mouvement FROM mouvements_stock WHERE document_type='retour_vendeur' "
                        "ORDER BY id DESC LIMIT 1").fetchone()[0] == "RETOUR_ACHAT"


def test_un_produit_avec_plusieurs_motifs_et_decisions_distinctes(conn):
    v1, p1, p2, r = _confirme(conn, [("p1", 3, "INVENDU"), ("p1", 1, "CASSE")])
    assert camion(conn, v1, p1) == 50 and tampon(conn, p1) == 200      # 250 - 4 colis x 50
    a, b = r["lignes"]
    rtv.decider_ligne(conn, a["id"], "VENDABLE", "Admin")
    rtv.decider_ligne(conn, b["id"], "CASSE", "Admin", "ENTREPRISE")
    assert depot(conn, p1) == 250 + 150 and tampon(conn, p1) == 0
    assert rtv.compter_a_traiter(conn)["total"] == 0


def test_decision_definitive_et_seulement_apres_confirmation(conn):
    v1, _, p1, _ = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU")])
    with pytest.raises(ValueError, match="d'abord être confirmé"):
        rtv.decider_ligne(conn, r["lignes"][0]["id"], "VENDABLE", "Admin")
    rtv.confirmer_retour(conn, r["id"], "Admin")
    rtv.decider_ligne(conn, r["lignes"][0]["id"], "VENDABLE", "Admin")
    with pytest.raises(ValueError, match="déjà été prise"):
        rtv.decider_ligne(conn, r["lignes"][0]["id"], "CASSE", "Admin", "VENDEUR")
    with pytest.raises(ValueError, match="Décision inconnue"):
        rtv.decider_ligne(conn, r["lignes"][0]["id"], "BIDON", "Admin")
    assert depot(conn, p1) == 300            # un seul retour en stock


# ───────────── règles de la demande / confirmation / rejet ─────────────

@pytest.mark.parametrize("lignes, message", [
    ([(1, 6, "INVENDU")], "disponible"),                       # plus que le camion (5 colis)
    ([(1, 3, "INVENDU"), (1, 3, "CASSE")], "disponible"),     # cumul > camion
    ([(1, 0, "INVENDU")], "supérieure à zéro"),
    ([(1, -2, "INVENDU")], "supérieure à zéro"),
    ([(1, 1, "")], "motif du retour est obligatoire"),
    ([(1, 1, "BIDON")], "motif du retour est obligatoire"),
    ([(1, 1, "AUTRE")], "précisez la raison"),
    ([(99, 1, "INVENDU")], "n'existe pas"),
    ([], "au moins un produit"),
])
def test_demande_refusee_sans_rien_creer(conn, lignes, message):
    v1, _, p1, p2 = charge(conn)
    assert (p1, p2) == (1, 2)
    with pytest.raises(ValueError, match=message):
        rtv.creer_demande_retour(conn, v1, lignes)
    assert conn.execute("SELECT COUNT(*) FROM retours_vendeur").fetchone()[0] == 0


def test_motif_autre_avec_commentaire_accepte(conn):
    v1, _, p1, _ = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1, 1, "AUTRE", "client absent")])
    assert r["lignes"][0]["commentaire"] == "client absent"


def test_deux_demandes_ne_peuvent_pas_promettre_plus_que_le_camion(conn):
    v1, _, p1, _ = charge(conn)
    rtv.creer_demande_retour(conn, v1, [(p1, 4, "INVENDU")])
    with pytest.raises(ValueError, match="disponible"):
        rtv.creer_demande_retour(conn, v1, [(p1, 2, "INVENDU")])
    rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU")])        # il reste exactement 1 colis


def test_confirmation_refusee_si_le_camion_a_baisse_entre_temps(conn):
    v1, _, p1, _ = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1, 4, "INVENDU")])
    conn.execute("UPDATE stock_camion_vendeur SET quantite_pieces=100 WHERE vendeur_id=? AND produit_id=?", (v1, p1))
    conn.commit()
    with pytest.raises(ValueError, match="ne contient plus assez"):
        rtv.confirmer_retour(conn, r["id"], "Admin")
    assert camion(conn, v1, p1) == 100 and tampon(conn, p1) in (0, None)
    assert rtv.detail_retour(conn, r["id"])["statut"] == "En attente"


def test_rejet_motif_obligatoire_rien_ne_bouge(conn):
    v1, _, p1, _ = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU")])
    with pytest.raises(ValueError, match="motif du rejet"):
        rtv.rejeter_retour(conn, r["id"], "Admin", " ")
    res = rtv.rejeter_retour(conn, r["id"], "Admin", "Recompter")
    assert res["statut"] == "Rejeté" and camion(conn, v1, p1) == 250
    with pytest.raises(ValueError, match="déjà « Rejeté »"):
        rtv.confirmer_retour(conn, r["id"], "Admin")


def test_pas_de_double_confirmation_ni_annulation_apres_decision(conn):
    v1, p1, _, r = _confirme(conn, [("p1", 1, "INVENDU")])
    with pytest.raises(ValueError, match="déjà « Confirmé »"):
        rtv.confirmer_retour(conn, r["id"], "Admin")
    with pytest.raises(ValueError, match="déjà « Confirmé »"):
        rtv.annuler_demande_retour(conn, r["id"], v1)
    assert camion(conn, v1, p1) == 200


def test_annulation_par_le_vendeur_seulement_pour_sa_demande(conn):
    v1, v2, p1, _ = charge(conn)
    r = rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU")])
    with pytest.raises(ValueError, match="introuvable"):
        rtv.annuler_demande_retour(conn, r["id"], v2)
    assert rtv.annuler_demande_retour(conn, r["id"], v1)["statut"] == "Annulé"
    rtv.creer_demande_retour(conn, v1, [(p1, 5, "INVENDU")])        # la quantité est de nouveau libre


# ───────────── tableaux de bord ─────────────

def test_listes_compteurs_et_situation_du_depot(conn):
    v1, _, p1, p2 = charge(conn)
    r1 = rtv.creer_demande_retour(conn, v1, [(p1, 1, "INVENDU"), (p2, 1, "CASSE")], observations="fin de tournée")
    assert rtv.compter_a_traiter(conn) == {"demandes": 1, "lignes": 0, "total": 1}
    rtv.confirmer_retour(conn, r1["id"], "Admin")
    assert rtv.compter_a_traiter(conn) == {"demandes": 0, "lignes": 2, "total": 2}
    a_traiter = rtv.lignes_a_traiter(conn)
    assert {x["designation"]: x["colis"] for x in a_traiter} == {"Produit Un": 1, "Produit Deux": 1}
    assert {x["motif"] for x in a_traiter} == {"INVENDU", "CASSE"}
    sit = rtv.situation_depot(conn)
    assert sit["retours_a_traiter_valeur"] == 50 * 5 + 6 * 20 and sit["lignes_a_decider"] == 2
    assert sit["stock_camions_valeur"] == (200 * 5) + (18 * 20)
    lst = rtv.lister_retours(conn, vendeur_id=v1)
    assert lst[0]["nb_lignes"] == 2 and lst[0]["lignes_a_decider"] == 2 and lst[0]["total_pieces"] == 56


# ───────────── API portail vendeur ─────────────

@pytest.fixture
def api(conn):
    app.dependency_overrides[get_db] = lambda: (yield conn)
    yield TestClient(app), conn
    app.dependency_overrides.clear()


def hdr(client, code="V1"):
    r = client.post("/auth/login-vendeur", json={"code_vendeur": code, "password": "Pass12345"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_api_flux_complet(api):
    client, conn = api
    v1, _, p1, p2 = charge(conn)
    h = hdr(client)

    motifs = client.get("/tournee/retours-vendeur/motifs", headers=h).json()
    assert {"code": "INVENDU", "libelle": "Invendu"} in motifs

    r = client.post("/tournee/retour-vendeur", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 1, "motif": "INVENDU"}], "retourne_par": "Karim"})
    assert r.status_code == 201, r.text
    bon = r.json()
    assert bon["statut"] == "En attente" and bon["retourne_par"] == "Karim"
    assert camion(conn, v1, p1) == 250

    assert [b["numero"] for b in client.get("/tournee/retours-vendeur", headers=h).json()] == [bon["numero"]]
    rtv.confirmer_retour(conn, bon["id"], "Admin")                 # côté administration
    vu = client.get(f"/tournee/retours-vendeur/{bon['id']}", headers=h).json()
    assert vu["statut"] == "Confirmé" and camion(conn, v1, p1) == 200


def test_api_validations_isolation_et_annulation(api):
    client, conn = api
    v1, v2, p1, p2 = charge(conn)
    h, h2 = hdr(client), hdr(client, "V2")

    assert client.post("/tournee/retour-vendeur", json={"lignes": []}).status_code in (401, 403)
    assert client.post("/tournee/retour-vendeur", headers=h, json={"lignes": []}).status_code == 422
    assert client.post("/tournee/retour-vendeur", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 99, "motif": "INVENDU"}]}).status_code == 400
    assert client.post("/tournee/retour-vendeur", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 1, "motif": "N'IMPORTE QUOI"}]}).status_code == 400
    assert client.post("/tournee/retour-vendeur", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 0, "motif": "INVENDU"}]}).status_code == 422

    bon = client.post("/tournee/retour-vendeur", headers=h, json={
        "lignes": [{"produit_id": p1, "quantite_colis": 1, "motif": "INVENDU"}]}).json()
    assert client.get("/tournee/retours-vendeur", headers=h2).json() == []
    assert client.get(f"/tournee/retours-vendeur/{bon['id']}", headers=h2).status_code == 404
    assert client.post(f"/tournee/retours-vendeur/{bon['id']}/annuler", headers=h2).status_code == 400
    assert client.post(f"/tournee/retours-vendeur/{bon['id']}/annuler", headers=h).json()["statut"] == "Annulé"


def test_migration_base_existante_ajoute_la_zone_retours():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_schema(c)
    c.executescript("""
        ALTER TABLE produits DROP COLUMN stock_retours_pieces;
        INSERT INTO produits (code, designation, unite, stock_actuel, actif) VALUES ('X','Ancien','U',7,1);
    """)
    init_schema(c)
    assert "stock_retours_pieces" in [r[1] for r in c.execute("PRAGMA table_info(produits)")]
    assert c.execute("SELECT stock_actuel, stock_retours_pieces FROM produits WHERE code='X'").fetchone()[0] == 7
    c.close()
