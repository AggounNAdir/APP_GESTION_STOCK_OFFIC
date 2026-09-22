"""
Tests du journal des mouvements de stock (api/stock_journal.py) et des
opérations de stock de modules/core.py qui l'alimentent.

Tout s'exécute sur une base SQLite EN MÉMOIRE créée avec le schéma réel
(api/schema.init_schema) : aucune dépendance à la vraie base.

    python -m pytest tests/test_stock_journal.py
"""
import random
import sqlite3

import pytest

from api import stock_journal as sj
from api.schema import init_schema


# ═══════════════════════════ OUTILS ═══════════════════════════

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    yield c
    c.close()


def _produit(conn, code="P1", stock=0.0, pmp=0.0, cout=0.0, prix_achat=0.0, unite="Pcs"):
    cur = conn.execute(
        """INSERT INTO produits(code, designation, unite, prix_achat, prix_vente,
               stock_actuel, prix_moyen_pondere, cout_total_stock)
           VALUES(?,?,?,?,?,?,?,?)""",
        (code, f"Produit {code}", unite, prix_achat, prix_achat * 1.3, stock, pmp, cout))
    return cur.lastrowid


def _stock(conn, pid):
    return conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (pid,)).fetchone()[0]


def _mouvements(conn, pid=None):
    sql = "SELECT * FROM mouvements_stock"
    args = ()
    if pid is not None:
        sql += " WHERE produit_id=?"
        args = (pid,)
    return conn.execute(sql + " ORDER BY id", args).fetchall()


def _somme_journal(conn, pid):
    return sj.stock_selon_journal(conn, pid)


# ═══════════════════════════ SCHÉMA / AJOUT SEUL ═══════════════════════════

def test_table_et_index_crees(conn):
    noms = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert "mouvements_stock" in noms
    assert {"idx_mvt_produit", "idx_mvt_date", "idx_mvt_document", "idx_mvt_type"} <= noms


def test_journal_en_ajout_seul(conn):
    pid = _produit(conn)
    sj.enregistrer_mouvement(conn, pid, "AJUSTEMENT", 0, 5, motif="test")
    with pytest.raises(sqlite3.IntegrityError, match="lecture seule"):
        conn.execute("UPDATE mouvements_stock SET quantite = 99")
    with pytest.raises(sqlite3.IntegrityError, match="lecture seule"):
        conn.execute("DELETE FROM mouvements_stock")
    assert len(_mouvements(conn)) == 1


def test_produit_avec_historique_non_supprimable(conn):
    pid = _produit(conn)
    sj.enregistrer_mouvement(conn, pid, "AJUSTEMENT", 0, 5)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM produits WHERE id=?", (pid,))


def test_init_schema_idempotent(conn):
    pid = _produit(conn, stock=10)
    init_schema(conn)
    init_schema(conn)
    assert len(_mouvements(conn, pid)) == 1   # une seule reprise, jamais doublée


# ═══════════════════════════ enregistrer_mouvement ═══════════════════════════

def test_enregistrer_quantite_signee_et_valeur(conn):
    pid = _produit(conn)
    mid = sj.enregistrer_mouvement(conn, pid, "VENTE", 10, 7, cout_unitaire=50, motif=" vente ")
    m = conn.execute("SELECT * FROM mouvements_stock WHERE id=?", (mid,)).fetchone()
    assert m["quantite"] == -3
    assert m["stock_avant"] == 10 and m["stock_apres"] == 7
    assert m["valeur"] == -150
    assert m["motif"] == "vente"
    assert m["utilisateur"]            # rempli automatiquement
    assert m["date_mouvement"]


def test_variation_nulle_non_journalisee(conn):
    pid = _produit(conn)
    assert sj.enregistrer_mouvement(conn, pid, "VENTE", 5, 5) is None
    assert _mouvements(conn) == []


def test_type_inconnu_refuse(conn):
    pid = _produit(conn)
    with pytest.raises(ValueError):
        sj.enregistrer_mouvement(conn, pid, "N_IMPORTE_QUOI", 0, 1)


def test_utilisateur_courant(conn):
    pid = _produit(conn)
    sj.set_utilisateur_courant("Karim")
    try:
        sj.enregistrer_mouvement(conn, pid, "AJUSTEMENT", 0, 1)
        sj.enregistrer_mouvement(conn, pid, "AJUSTEMENT", 1, 2, utilisateur="Amina")
    finally:
        sj.set_utilisateur_courant(None)
    assert [m["utilisateur"] for m in _mouvements(conn)] == ["Karim", "Amina"]


def test_document_resolu_automatiquement(conn):
    pid = _produit(conn)
    cid = conn.execute("INSERT INTO clients(code, nom) VALUES('C1','Client Alpha')").lastrowid
    bon = conn.execute(
        "INSERT INTO bons_vente(numero, date_bon, client_id) VALUES('BV-00001','2026-05-04',?)",
        (cid,)).lastrowid
    # l'id peut arriver en texte (iid d'un Treeview)
    sj.enregistrer_mouvement(conn, pid, "VENTE", 10, 8, document_type="bon_vente",
                             document_id=str(bon))
    m = _mouvements(conn)[0]
    assert (m["document_numero"], m["tiers_nom"], m["date_document"]) == \
           ("BV-00001", "Client Alpha", "2026-05-04")
    assert m["document_id"] == bon


def test_numero_conserve_apres_suppression_du_bon(conn):
    pid = _produit(conn)
    cid = conn.execute("INSERT INTO clients(code, nom) VALUES('C1','Client Alpha')").lastrowid
    bon = conn.execute(
        "INSERT INTO bons_vente(numero, date_bon, client_id) VALUES('BV-9','2026-01-01',?)",
        (cid,)).lastrowid
    sj.enregistrer_mouvement(conn, pid, "VENTE", 5, 3, document_type="bon_vente", document_id=bon)
    conn.execute("DELETE FROM bons_vente WHERE id=?", (bon,))
    m = _mouvements(conn)[0]
    assert m["document_numero"] == "BV-9" and m["tiers_nom"] == "Client Alpha"


def test_document_inconnu_ne_bloque_pas(conn):
    pid = _produit(conn)
    sj.enregistrer_mouvement(conn, pid, "VENTE", 5, 3, document_type="bon_vente", document_id=999)
    assert _mouvements(conn)[0]["document_numero"] is None


def test_rollback_annule_aussi_le_mouvement(conn):
    pid = _produit(conn)
    conn.commit()
    sj.enregistrer_mouvement(conn, pid, "AJUSTEMENT", 0, 5)
    conn.rollback()
    assert _mouvements(conn) == []


# ═══════════════════════════ REPRISE ═══════════════════════════

def test_reprise_du_stock_existant(conn):
    a = _produit(conn, "A", stock=10, pmp=25)
    b = _produit(conn, "B", stock=-4, prix_achat=8)        # stock négatif, pas de PMP
    c = _produit(conn, "C", stock=0)                        # rien à reprendre
    d = _produit(conn, "D", stock=6)
    sj.enregistrer_mouvement(conn, d, "ACHAT", 0, 6)        # déjà journalisé
    assert sj.reprise_stock_existant(conn) == 2
    ma, mb = _mouvements(conn, a)[0], _mouvements(conn, b)[0]
    assert (ma["type_mouvement"], ma["quantite"], ma["stock_avant"], ma["stock_apres"]) == \
           ("REPRISE", 10, 0, 10)
    assert ma["cout_unitaire"] == 25 and ma["valeur"] == 250
    assert mb["quantite"] == -4 and mb["cout_unitaire"] == 8    # repli sur le prix d'achat
    assert _mouvements(conn, c) == []
    assert len(_mouvements(conn, d)) == 1
    assert sj.reprise_stock_existant(conn) == 0                 # idempotent
    assert sj.verifier_coherence(conn) == []


# ═══════════════════════════ COHÉRENCE ═══════════════════════════

def test_coherence_detecte_et_regularise(conn):
    pid = _produit(conn, stock=10)
    sj.reprise_stock_existant(conn)
    assert sj.verifier_coherence(conn) == []

    # modification « hors journal » (script, import, ancienne version...)
    conn.execute("UPDATE produits SET stock_actuel = 14 WHERE id=?", (pid,))
    ecarts = sj.verifier_coherence(conn)
    assert len(ecarts) == 1
    assert (ecarts[0]["stock_actuel"], ecarts[0]["stock_journal"], ecarts[0]["ecart"]) == (14, 10, 4)

    assert sj.regulariser_ecarts(conn, [pid]) == 1
    assert sj.verifier_coherence(conn) == []
    assert _stock(conn, pid) == 14                           # le stock n'est pas touché
    last = _mouvements(conn, pid)[-1]
    assert last["type_mouvement"] == "REGULARISATION" and last["quantite"] == 4
    assert sj.regulariser_ecarts(conn) == 0


def test_regularisation_limitee_aux_produits_choisis(conn):
    a = _produit(conn, "A", stock=5)
    b = _produit(conn, "B", stock=5)
    sj.reprise_stock_existant(conn)
    conn.execute("UPDATE produits SET stock_actuel = stock_actuel + 1")
    assert sj.regulariser_ecarts(conn, [a]) == 1
    assert [e["produit_id"] for e in sj.verifier_coherence(conn)] == [b]


# ═══════════════════════════ RECHERCHE / TOTAUX ═══════════════════════════

@pytest.fixture
def jeu(conn):
    """Quelques mouvements à des dates différentes."""
    p1 = _produit(conn, "P1")
    p2 = _produit(conn, "P2")
    lignes = [
        (p1, "ACHAT", 0, 100, 10.0, "2026-05-01 09:00:00", "Réception spéciale 100%"),
        (p1, "VENTE", 100, 70, 10.0, "2026-05-02 10:00:00", None),
        (p2, "ACHAT", 0, 50, 4.0, "2026-05-02 23:59:59", None),
        (p1, "AJUSTEMENT", 70, 68, 10.0, "2026-05-03 08:00:00", "casse"),
    ]
    for pid, typ, av, ap, cout, dt, motif in lignes:
        mid = sj.enregistrer_mouvement(conn, pid, typ, av, ap, cout_unitaire=cout, motif=motif)
        conn.execute("DROP TRIGGER trg_mvt_stock_no_update")   # fixe la date pour le test
        conn.execute("UPDATE mouvements_stock SET date_mouvement=? WHERE id=?", (dt, mid))
        conn.executescript("""CREATE TRIGGER trg_mvt_stock_no_update BEFORE UPDATE ON mouvements_stock
            BEGIN SELECT RAISE(ABORT, 'Journal des mouvements de stock en lecture seule'); END;""")
    return {"p1": p1, "p2": p2}


def test_recherche_plus_recent_d_abord(conn, jeu):
    ids = [m["id"] for m in sj.rechercher_mouvements(conn)]
    assert ids == sorted(ids, reverse=True) and len(ids) == 4


def test_filtre_periode_inclut_les_bornes(conn, jeu):
    r = sj.rechercher_mouvements(conn, date_debut="2026-05-02", date_fin="2026-05-02")
    assert len(r) == 2        # y compris le mouvement de 23:59:59
    assert len(sj.rechercher_mouvements(conn, date_debut="2026-05-03")) == 1
    assert len(sj.rechercher_mouvements(conn, date_fin="2026-05-01")) == 1


def test_filtres_produit_type_sens(conn, jeu):
    assert len(sj.rechercher_mouvements(conn, produit_id=jeu["p2"])) == 1
    assert len(sj.rechercher_mouvements(conn, types=["VENTE", "AJUSTEMENT"])) == 2
    assert len(sj.rechercher_mouvements(conn, sens="entree")) == 2
    assert len(sj.rechercher_mouvements(conn, sens="sortie")) == 2


def test_recherche_texte_et_caracteres_speciaux(conn, jeu):
    assert len(sj.rechercher_mouvements(conn, texte="casse")) == 1
    assert len(sj.rechercher_mouvements(conn, texte="P2")) == 1          # code produit
    assert len(sj.rechercher_mouvements(conn, texte="100%")) == 1        # % littéral
    assert len(sj.rechercher_mouvements(conn, texte="%")) == 1           # pas un joker
    assert len(sj.rechercher_mouvements(conn, texte="_")) == 0           # pas un joker


def test_pagination(conn, jeu):
    page1 = sj.rechercher_mouvements(conn, limite=3, offset=0)
    page2 = sj.rechercher_mouvements(conn, limite=3, offset=3)
    assert len(page1) == 3 and len(page2) == 1
    assert not {m["id"] for m in page1} & {m["id"] for m in page2}
    assert len(sj.rechercher_mouvements(conn, limite=None)) == 4


def test_infos_produit_dans_les_resultats(conn, jeu):
    m = sj.rechercher_mouvements(conn, produit_id=jeu["p2"])[0]
    assert (m["produit_code"], m["produit_designation"], m["produit_unite"]) == \
           ("P2", "Produit P2", "Pcs")


def test_totaux(conn, jeu):
    t = sj.totaliser_mouvements(conn)
    assert t["nombre"] == 4
    assert t["entrees"] == 150 and t["sorties"] == 32           # 30 + 2
    assert t["valeur_entrees"] == 100 * 10 + 50 * 4 == 1200
    assert t["valeur_sorties"] == 30 * 10 + 2 * 10 == 320
    assert sj.totaliser_mouvements(conn, produit_id=jeu["p2"])["nombre"] == 1
    vide = sj.totaliser_mouvements(conn, texte="introuvable")
    assert vide["nombre"] == 0 and vide["entrees"] == 0


# ═══════════════════════════ OPÉRATIONS DE STOCK (modules/core.py) ═══════════════════════════

core = pytest.importorskip("modules.core", reason="tkinter requis pour importer modules.core")


def test_achats_pmp_et_journal(conn):
    pid = _produit(conn)
    core.entree_stock_achat(conn, pid, 10, 100, document_type="bon_achat", document_id=1)
    pmp, cout = core.entree_stock_achat(conn, pid, 10, 200)
    assert (pmp, cout) == (150, 3000)                       # même résultat qu'avant le journal
    p = conn.execute("SELECT * FROM produits WHERE id=?", (pid,)).fetchone()
    assert (p["stock_actuel"], p["prix_moyen_pondere"], p["cout_total_stock"], p["prix_achat"]) == \
           (20, 150, 3000, 200)
    m1, m2 = _mouvements(conn, pid)
    assert (m1["type_mouvement"], m1["quantite"], m1["stock_avant"], m1["stock_apres"]) == \
           ("ACHAT", 10, 0, 10)
    assert (m2["quantite"], m2["stock_avant"], m2["stock_apres"], m2["pmp_apres"]) == (10, 10, 20, 150)
    assert m2["cout_unitaire"] == 200 and m2["valeur"] == 2000


def test_entree_achat_sans_maj_prix_achat(conn):
    pid = _produit(conn, prix_achat=77)
    core.entree_stock_achat(conn, pid, 5, 100, maj_prix_achat=False,
                            type_mouvement="ANNULATION_RETOUR_ACHAT")
    assert conn.execute("SELECT prix_achat FROM produits WHERE id=?", (pid,)).fetchone()[0] == 77
    assert _mouvements(conn, pid)[0]["type_mouvement"] == "ANNULATION_RETOUR_ACHAT"


def test_vente_sortie_au_pmp(conn):
    pid = _produit(conn)
    core.entree_stock_achat(conn, pid, 20, 150)
    core.recalculer_cout_stock_apres_sortie(conn, pid, 5, document_type="bon_vente", document_id=1)
    p = conn.execute("SELECT * FROM produits WHERE id=?", (pid,)).fetchone()
    assert (p["stock_actuel"], p["prix_moyen_pondere"], p["cout_total_stock"]) == (15, 150, 2250)
    m = _mouvements(conn, pid)[-1]
    assert (m["type_mouvement"], m["quantite"], m["cout_unitaire"], m["valeur"]) == \
           ("VENTE", -5, 150, -750)
    assert (m["stock_avant"], m["stock_apres"]) == (20, 15)


def test_annulation_de_vente_reintegre_au_pmp(conn):
    pid = _produit(conn)
    core.entree_stock_achat(conn, pid, 20, 150)
    core.recalculer_cout_stock_apres_sortie(conn, pid, 5)
    core.entree_stock_annulation_vente(conn, pid, 5, motif="Annulation du bon")
    assert _stock(conn, pid) == 20
    m = _mouvements(conn, pid)[-1]
    assert (m["type_mouvement"], m["quantite"], m["cout_unitaire"], m["motif"]) == \
           ("ANNULATION_VENTE", 5, 150, "Annulation du bon")


def test_sortie_de_quantite_nulle_sans_ligne(conn):
    pid = _produit(conn, stock=5)
    sj.reprise_stock_existant(conn)
    core.recalculer_cout_stock_apres_sortie(conn, pid, 0)
    assert len(_mouvements(conn, pid)) == 1


def test_inversion_achat_normale(conn):
    pid = _produit(conn)
    core.entree_stock_achat(conn, pid, 10, 100)
    ligne = {"produit_id": pid, "quantite": 10, "prix_unitaire": 100, "total": 1000}
    core.inverser_stock_achat(conn, [ligne], document_type="bon_achat", document_id=1,
                              motif="Annulation du bon d'achat")
    assert _stock(conn, pid) == 0
    m = _mouvements(conn, pid)[-1]
    assert (m["type_mouvement"], m["quantite"], m["cout_unitaire"]) == ("ANNULATION_ACHAT", -10, 100)
    assert m["motif"] == "Annulation du bon d'achat"


def test_inversion_achat_plafonnee_journalise_le_delta_reel(conn):
    """Stock insuffisant : le retrait est plafonné à 0 (comportement historique).
    Le journal enregistre ce qui s'est réellement passé, pour rester cohérent."""
    pid = _produit(conn)
    core.entree_stock_achat(conn, pid, 10, 100)
    core.recalculer_cout_stock_apres_sortie(conn, pid, 7)             # reste 3
    ligne = {"produit_id": pid, "quantite": 10, "prix_unitaire": 100, "total": 1000}
    core.inverser_stock_achat(conn, [ligne])
    assert _stock(conn, pid) == 0
    m = _mouvements(conn, pid)[-1]
    assert m["quantite"] == -3
    assert "limité à 3 sur 10" in m["motif"]
    assert sj.verifier_coherence(conn) == []


# ═══════════════════════════ AJUSTEMENT MANUEL ═══════════════════════════

def test_ajustement_delta_et_fixer(conn):
    pid = _produit(conn)
    core.entree_stock_achat(conn, pid, 10, 100)
    assert core.ajuster_stock_manuel(conn, pid, "Casse", delta=-2) == -2
    assert _stock(conn, pid) == 8
    assert core.ajuster_stock_manuel(conn, pid, "Inventaire", nouveau_stock=12) == 4
    assert _stock(conn, pid) == 12
    m_casse, m_inv = _mouvements(conn, pid)[-2:]
    assert (m_casse["type_mouvement"], m_casse["quantite"], m_casse["motif"]) == \
           ("AJUSTEMENT", -2, "Casse")
    assert (m_inv["quantite"], m_inv["stock_avant"], m_inv["stock_apres"]) == (4, 8, 12)
    p = conn.execute("SELECT * FROM produits WHERE id=?", (pid,)).fetchone()
    assert p["cout_total_stock"] == pytest.approx(1200)         # valorisé au PMP


def test_ajustement_sans_changement_ou_invalide(conn):
    pid = _produit(conn, stock=5)
    sj.reprise_stock_existant(conn)
    assert core.ajuster_stock_manuel(conn, pid, "Contrôle", nouveau_stock=5) == 0
    assert len(_mouvements(conn, pid)) == 1
    with pytest.raises(ValueError):
        core.ajuster_stock_manuel(conn, pid, "  ", delta=1)               # motif vide
    with pytest.raises(ValueError):
        core.ajuster_stock_manuel(conn, pid, "x")                          # ni delta ni stock
    with pytest.raises(ValueError):
        core.ajuster_stock_manuel(conn, pid, "x", delta=1, nouveau_stock=2)
    with pytest.raises(ValueError):
        core.ajuster_stock_manuel(conn, 12345, "x", delta=1)               # produit inconnu


# ═══════════════════════════ INVARIANT GLOBAL ═══════════════════════════

def test_invariant_stock_egal_somme_du_journal(conn):
    """Après n'importe quelle suite d'opérations, stock_actuel == SUM(journal)."""
    rnd = random.Random(42)
    pids = [_produit(conn, f"P{i}") for i in range(3)]
    for _ in range(300):
        pid = rnd.choice(pids)
        op = rnd.choice(["achat", "vente", "annul_vente", "ajust", "fixer", "inv_achat"])
        q = rnd.randint(1, 20)
        if op == "achat":
            core.entree_stock_achat(conn, pid, q, rnd.randint(50, 300))
        elif op == "vente":
            core.recalculer_cout_stock_apres_sortie(conn, pid, q)
        elif op == "annul_vente":
            core.entree_stock_annulation_vente(conn, pid, q)
        elif op == "ajust":
            core.ajuster_stock_manuel(conn, pid, "test", delta=rnd.choice([-1, 1]) * q)
        elif op == "fixer":
            core.ajuster_stock_manuel(conn, pid, "test", nouveau_stock=q)
        else:
            core.inverser_stock_achat(
                conn, [{"produit_id": pid, "quantite": q, "prix_unitaire": 100, "total": q * 100}])
    assert sj.verifier_coherence(conn) == []
    for pid in pids:
        assert _somme_journal(conn, pid) == pytest.approx(_stock(conn, pid))
        # chaînage : le stock « avant » de chaque ligne = le stock « après » de la précédente
        precedent = 0
        for m in _mouvements(conn, pid):
            assert m["stock_avant"] == pytest.approx(precedent)
            precedent = m["stock_apres"]
