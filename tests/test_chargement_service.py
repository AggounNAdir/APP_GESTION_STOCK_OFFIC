import sqlite3

import pytest

from api.chargement_service import creer_bon_chargement, decharger_camion
from api.schema import init_schema


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
