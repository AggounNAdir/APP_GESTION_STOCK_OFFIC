import sqlite3

import pytest

from api import vendeur_dossier
from api.chargement_service import (
    annuler_bon_chargement,
    creer_bon_chargement,
    decharger_camion,
    modifier_bon_chargement,
    supprimer_bon_chargement,
)
from api.schema import init_schema
from api.stock_journal import reprise_stock_existant


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_schema(connection)
    connection.execute(
        "INSERT INTO vendeurs(code, nom, actif) VALUES('VEN-01', 'Vendeur Test', 1)"
    )
    connection.execute(
        """INSERT INTO produits
           (code, designation, unite, facteur_conversion, stock_actuel, actif)
           VALUES('PRD-01', 'Produit Test', 'Carton', 12, 120, 1)"""
    )
    reprise_stock_existant(connection)
    connection.commit()
    yield connection
    connection.close()


def test_creation_bon_transfere_stock_et_journalise(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]

    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 3)], "Tournée matin")

    assert bon["numero"].startswith("CHG-")
    assert bon["total_colis"] == 3
    assert bon["total_pieces"] == 36
    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 84
    stock_camion = conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()
    assert tuple(stock_camion) == (3, 36)
    assert conn.execute(
        "SELECT quantite FROM mouvements_stock WHERE document_id=? AND type_mouvement='CHARGEMENT_CAMION'",
        (bon["id"],),
    ).fetchone()[0] == -36


def test_chargement_refuse_si_stock_insuffisant_sans_modification(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]

    with pytest.raises(ValueError, match="Stock insuffisant"):
        creer_bon_chargement(conn, vendeur_id, [(produit_id, 11)])

    assert conn.execute("SELECT COUNT(*) FROM bons_chargement").fetchone()[0] == 0
    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 120


def test_dechargement_reintegre_stock_et_vide_camion(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])

    resultat = decharger_camion(conn, vendeur_id)

    assert resultat == {"produits": 1, "total_colis": 2, "total_pieces": 24}
    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 120
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()) == (0, 0)
    assert conn.execute(
        "SELECT quantite FROM mouvements_stock WHERE type_mouvement='RETOUR_CAMION'"
    ).fetchone()[0] == 24


def test_modification_ajuste_stock_et_conserve_le_journal(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)], "Matin")

    modifier_bon_chargement(conn, bon["id"], [(produit_id, 3)], "Après correction")

    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 84
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()) == (3, 36)
    assert conn.execute(
        "SELECT quantite FROM mouvements_stock WHERE type_mouvement='CORRECTION_CHARGEMENT'"
    ).fetchone()[0] == -12
    assert tuple(conn.execute(
        "SELECT observations, total_colis FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()) == ("Après correction", 3)

    modifier_bon_chargement(conn, bon["id"], [(produit_id, 1)])

    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 108
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()) == (1, 12)
    assert conn.execute(
        "SELECT SUM(quantite) FROM mouvements_stock WHERE produit_id=?",
        (produit_id,),
    ).fetchone()[0] == conn.execute(
        "SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)
    ).fetchone()[0]


def test_modification_refuse_si_stock_camion_insuffisant(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])
    conn.execute(
        """UPDATE stock_camion_vendeur SET quantite_colis=1, quantite_pieces=12
           WHERE vendeur_id=? AND produit_id=?""",
        (vendeur_id, produit_id),
    )
    conn.commit()

    with pytest.raises(ValueError, match="stock disponible dans le camion"):
        modifier_bon_chargement(conn, bon["id"], [(produit_id, 0.5)])

    assert conn.execute(
        "SELECT statut FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == "Validé"
    assert conn.execute(
        "SELECT total_colis FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == 2


def test_annulation_retourne_le_stock_et_garde_le_bon_trace(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])

    annuler_bon_chargement(conn, bon["id"])

    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 120
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()) == (0, 0)
    assert conn.execute(
        "SELECT statut FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == "Annulé"
    assert conn.execute(
        "SELECT quantite FROM mouvements_stock WHERE type_mouvement='ANNULATION_CHARGEMENT'"
    ).fetchone()[0] == 24
    assert conn.execute(
        "SELECT SUM(quantite) FROM mouvements_stock WHERE produit_id=?",
        (produit_id,),
    ).fetchone()[0] == 120
    assert vendeur_dossier.situation_vendeur(conn, vendeur_id)["nb_chargements"] == 0
    with pytest.raises(ValueError, match="validé peut être annulé"):
        annuler_bon_chargement(conn, bon["id"])
    with pytest.raises(ValueError, match="validé peut être modifié"):
        modifier_bon_chargement(conn, bon["id"], [(produit_id, 1)])


def test_annulation_refuse_si_stock_camion_a_ete_utilise(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])
    conn.execute(
        """UPDATE stock_camion_vendeur SET quantite_colis=1, quantite_pieces=12
           WHERE vendeur_id=? AND produit_id=?""",
        (vendeur_id, produit_id),
    )
    conn.commit()

    with pytest.raises(ValueError, match="stock disponible dans le camion"):
        annuler_bon_chargement(conn, bon["id"])

    assert conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()[0] == 96
    assert conn.execute(
        "SELECT statut FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == "Validé"


def test_suppression_definitive_retourne_stock_et_efface_le_bon_et_son_journal(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])
    modifier_bon_chargement(conn, bon["id"], [(produit_id, 3)])

    resultat = supprimer_bon_chargement(conn, bon["id"])

    assert resultat["numero"] == bon["numero"]
    assert resultat["mouvements_supprimes"] == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM lignes_chargement WHERE chargement_id=?", (bon["id"],)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM mouvements_stock WHERE document_type='bon_chargement' AND document_id=?",
        (bon["id"],),
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)
    ).fetchone()[0] == 120
    assert tuple(conn.execute(
        "SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()) == (0, 0)
    assert conn.execute(
        "SELECT SUM(quantite) FROM mouvements_stock WHERE produit_id=?", (produit_id,)
    ).fetchone()[0] == 120
    with pytest.raises(sqlite3.IntegrityError, match="suppression interdite"):
        conn.execute("DELETE FROM mouvements_stock WHERE produit_id=?", (produit_id,))


def test_suppression_refuse_si_le_stock_du_bon_a_quitte_le_camion(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])
    conn.execute(
        """UPDATE stock_camion_vendeur SET quantite_colis=1, quantite_pieces=12
           WHERE vendeur_id=? AND produit_id=?""",
        (vendeur_id, produit_id),
    )
    conn.commit()

    with pytest.raises(ValueError, match="ne permet pas de retourner"):
        supprimer_bon_chargement(conn, bon["id"])

    assert conn.execute(
        "SELECT COUNT(*) FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM mouvements_stock WHERE document_type='bon_chargement' AND document_id=?",
        (bon["id"],),
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)
    ).fetchone()[0] == 96


def test_suppression_bon_deja_annule_ne_change_pas_le_stock(conn):
    vendeur_id = conn.execute("SELECT id FROM vendeurs WHERE code='VEN-01'").fetchone()[0]
    produit_id = conn.execute("SELECT id FROM produits WHERE code='PRD-01'").fetchone()[0]
    bon = creer_bon_chargement(conn, vendeur_id, [(produit_id, 2)])
    annuler_bon_chargement(conn, bon["id"])

    resultat = supprimer_bon_chargement(conn, bon["id"])

    assert resultat["mouvements_supprimes"] == 2
    assert conn.execute(
        "SELECT stock_actuel FROM produits WHERE id=?", (produit_id,)
    ).fetchone()[0] == 120
    assert conn.execute(
        "SELECT COUNT(*) FROM bons_chargement WHERE id=?", (bon["id"],)
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM mouvements_stock WHERE document_id=?", (bon["id"],)
    ).fetchone()[0] == 0
