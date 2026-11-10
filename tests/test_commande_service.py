import sqlite3

import pytest

pytest.importorskip("tkinter")  # modules.core importe tkinter

from api import vendeur_dossier as vd
from api.schema import init_schema
from modules import commande_service as cs


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    c.execute("INSERT INTO vendeurs(code, nom, actif) VALUES('V1', 'Ali', 1)")
    # 1 colis = 10 pièces ; stock dépôt = 100 pièces = 10 colis ; prix 50/pièce
    c.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion, prix_vente,
                                 stock_actuel, prix_moyen_pondere, cout_total_stock, actif)
           VALUES('P1', 'Produit', 'Carton', 10, 50, 100, 30, 3000, 1)""")
    c.execute("INSERT INTO clients(code, nom, solde) VALUES('C1', 'Client Un', 0)")
    c.execute(
        """INSERT INTO prospects_clients(code, nom, tel, vendeur_id, date_creation, statut, wilaya)
           VALUES('PR1', 'Prospect Un', '0555', 1, '2026-11-02T10:00:00', 'Nouveau', 'Alger')""")
    c.commit()
    yield c
    c.close()


def _client_id(c):
    # NB : le schéma crée déjà un client « COMPTOIR » : on retrouve « C1 » par son code.
    return c.execute("SELECT id FROM clients WHERE code='C1'").fetchone()[0]


def _nb_clients(c):
    return c.execute("SELECT COUNT(*) FROM clients").fetchone()[0]


def _cmd_client(c, colis, numero="CMD-1"):
    cur = c.execute(
        """INSERT INTO commandes_clients(numero, client_id, vendeur_id, date_commande, statut, total_estime)
           VALUES(?, ?, 1, '2026-11-10', 'En attente', 0)""", (numero, _client_id(c)))
    c.execute(
        """INSERT INTO lignes_commande_client(commande_id, produit_id, quantite,
                                              prix_unitaire_estime, total_estime)
           VALUES(?, 1, ?, 50, 0)""", (cur.lastrowid, colis))
    c.commit()
    return cur.lastrowid


def _cmd_prospect(c, colis, numero="CMD-P1"):
    cur = c.execute(
        """INSERT INTO commandes_prospects(numero, prospect_id, vendeur_id, date_commande, statut, montant_total)
           VALUES(?, 1, 1, '2026-11-10', 'En attente', 0)""", (numero,))
    c.execute(
        """INSERT INTO lignes_commande_prospect(commande_id, produit_id, quantite, prix_unitaire, total)
           VALUES(?, 1, ?, 50, 0)""", (cur.lastrowid, colis))
    c.commit()
    return cur.lastrowid


def _stock(c):
    return c.execute("SELECT stock_actuel FROM produits WHERE id=1").fetchone()[0]


def test_validation_client_cree_bon_rattache_au_vendeur(conn):
    cid = _cmd_client(conn, 4)               # 4 colis = 40 pièces = 2000 DA
    res = cs.valider_commande(conn, cs.TYPE_CLIENT, cid)

    assert res["total"] == 2000 and not res["ajuste"]
    assert _stock(conn) == 60                # 100 - 40 pièces
    bon = conn.execute("SELECT * FROM bons_vente WHERE id=?", (res["bon_id"],)).fetchone()
    assert bon["vendeur_id"] == 1 and bon["total"] == 2000 and bon["reste_payer"] == 2000
    assert bon["numero"].startswith(f"BV-{_client_id(conn):05d}-")
    ligne = conn.execute("SELECT quantite, total FROM lignes_vente WHERE bon_id=?",
                         (res["bon_id"],)).fetchone()
    assert ligne["quantite"] == 40 and ligne["total"] == 2000
    assert conn.execute("SELECT solde FROM clients WHERE id=?", (_client_id(conn),)).fetchone()[0] == 2000
    cmd = conn.execute("SELECT statut, bon_vente_id FROM commandes_clients WHERE id=?", (cid,)).fetchone()
    assert cmd["statut"] == "Validée" and cmd["bon_vente_id"] == res["bon_id"]
    # La vente apparaît dans la situation du vendeur
    s = vd.situation_vendeur(conn, 1)
    assert s["nb_ventes"] == 1 and s["ca"] == 2000 and s["credit_accorde"] == 2000
    assert s["commandes_en_attente"] == 0


def test_double_validation_refusee(conn):
    cid = _cmd_client(conn, 1)
    cs.valider_commande(conn, cs.TYPE_CLIENT, cid)
    with pytest.raises(ValueError, match="déjà"):
        cs.valider_commande(conn, cs.TYPE_CLIENT, cid)
    assert conn.execute("SELECT COUNT(*) FROM bons_vente").fetchone()[0] == 1
    assert _stock(conn) == 90


def test_stock_insuffisant_refuse_la_validation_totale_sans_rien_modifier(conn):
    cid = _cmd_client(conn, 12)              # 12 colis demandés, 10 disponibles
    with pytest.raises(ValueError, match="Stock insuffisant"):
        cs.valider_commande(conn, cs.TYPE_CLIENT, cid)
    assert _stock(conn) == 100
    assert conn.execute("SELECT COUNT(*) FROM bons_vente").fetchone()[0] == 0
    assert conn.execute("SELECT statut FROM commandes_clients WHERE id=?", (cid,)).fetchone()[0] == "En attente"


def test_validation_ajustee_limite_au_stock(conn):
    cid = _cmd_client(conn, 12)
    res = cs.valider_commande(conn, cs.TYPE_CLIENT, cid, complete=False)
    assert res["ajuste"] and res["total"] == 5000      # 10 colis = 100 pièces × 50
    assert _stock(conn) == 0
    obs = conn.execute("SELECT observations FROM commandes_clients WHERE id=?", (cid,)).fetchone()[0]
    assert "ajustée" in obs


def test_rejet_avec_motif_puis_validation_impossible(conn):
    cid = _cmd_client(conn, 1)
    cs.rejeter_commande(conn, cs.TYPE_CLIENT, cid, "Client en impayé")
    row = conn.execute("SELECT statut, observations FROM commandes_clients WHERE id=?", (cid,)).fetchone()
    assert row["statut"] == "Rejetée" and "Client en impayé" in row["observations"]
    with pytest.raises(ValueError):
        cs.valider_commande(conn, cs.TYPE_CLIENT, cid)
    with pytest.raises(ValueError):
        cs.rejeter_commande(conn, cs.TYPE_CLIENT, cid)
    assert _stock(conn) == 100


def test_prospect_exige_confirmation_de_conversion_puis_cree_le_client(conn):
    pid = _cmd_prospect(conn, 2)
    avant = _nb_clients(conn)
    with pytest.raises(cs.ConversionProspectRequise):
        cs.valider_commande(conn, cs.TYPE_PROSPECT, pid)
    assert _nb_clients(conn) == avant   # rien créé

    res = cs.valider_commande(conn, cs.TYPE_PROSPECT, pid, convertir_prospect=True)
    prospect = conn.execute("SELECT statut, client_id FROM prospects_clients WHERE id=1").fetchone()
    assert prospect["statut"] == "Converti" and prospect["client_id"] == res["client_id"]
    assert res["total"] == 1000 and _stock(conn) == 80
    assert conn.execute("SELECT vendeur_id FROM bons_vente WHERE id=?", (res["bon_id"],)).fetchone()[0] == 1
    assert conn.execute("SELECT statut FROM commandes_prospects WHERE id=?", (pid,)).fetchone()[0] == "Validée"

    # Prospect déjà converti : plus de confirmation nécessaire
    pid2 = _cmd_prospect(conn, 1, numero="CMD-P2")
    res2 = cs.valider_commande(conn, cs.TYPE_PROSPECT, pid2)
    assert res2["client_id"] == res["client_id"]
    assert res2["numero"] != res["numero"]


def test_conversion_prospect_annulee_si_la_validation_echoue(conn):
    pid = _cmd_prospect(conn, 50)            # bien plus que le stock
    avant = _nb_clients(conn)
    with pytest.raises(ValueError, match="Stock insuffisant"):
        cs.valider_commande(conn, cs.TYPE_PROSPECT, pid, convertir_prospect=True)
    assert conn.execute("SELECT statut FROM prospects_clients WHERE id=1").fetchone()[0] == "Nouveau"
    assert _nb_clients(conn) == avant   # client non créé
    assert _stock(conn) == 100


def test_detail_et_liste_des_commandes_du_vendeur(conn):
    cid = _cmd_client(conn, 3)
    lignes = cs.lignes_commande(conn, cs.TYPE_CLIENT, cid)
    assert lignes[0]["quantite"] == 3 and lignes[0]["facteur"] == 10 and lignes[0]["stock_pieces"] == 100
    liste = vd.commandes_vendeur(conn, 1)
    assert liste[0]["id"] == cid and liste[0]["type"] == "Client"
