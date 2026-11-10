import sqlite3

import pytest

from api import vendeur_dossier as vd
from api.chargement_service import creer_bon_chargement
from api.schema import init_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    c.execute("INSERT INTO vendeurs(code, nom, actif) VALUES('V1', 'Ali', 1)")
    c.execute("INSERT INTO vendeurs(code, nom, actif) VALUES('V2', 'Omar', 1)")
    c.execute(
        """INSERT INTO produits (code, designation, unite, facteur_conversion,
                                 prix_vente, stock_actuel, actif)
           VALUES('P1', 'Produit', 'Carton', 10, 100, 1000, 1)"""
    )
    c.execute("INSERT INTO clients(code, nom) VALUES('C1', 'Client Un')")
    c.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut, solde)
           VALUES('PR1', 'Prospect Un', 1, '2026-11-02T10:00:00', 'Nouveau', 500)"""
    )
    c.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut)
           VALUES('PR2', 'Prospect Autre', 2, '2026-11-02T10:00:00', 'Nouveau')"""
    )
    c.commit()
    yield c
    c.close()


def _vente(c, num, date, vendeur, total, verse, statut="Validé"):
    c.execute(
        """INSERT INTO bons_vente(numero, date_bon, client_id, vendeur_id, total,
                                  montant_verse, reste_payer, statut)
           VALUES(?, ?, 1, ?, ?, ?, ?, ?)""",
        (num, date, vendeur, total, verse, max(0, total - verse), statut),
    )


def _vers(c, table, num, date, vendeur, montant, mode="Espèces"):
    if table == "versements_clients":
        c.execute(
            """INSERT INTO versements_clients(numero, date_vers, client_id, montant, mode, vendeur_id)
               VALUES(?, ?, 1, ?, ?, ?)""", (num, date, montant, mode, vendeur))
    else:
        c.execute(
            """INSERT INTO versements_prospects(numero, date_vers, prospect_id, montant, mode, vendeur_id)
               VALUES(?, ?, 1, ?, ?, ?)""", (num, date, montant, mode, vendeur))


def test_situation_n_inclut_que_le_vendeur_et_exclut_les_annules(conn):
    _vente(conn, "B1", "2026-11-02", 1, 1000, 400)
    _vente(conn, "B2", "2026-11-03", 1, 500, 500)
    _vente(conn, "B3", "2026-11-03", 1, 9999, 0, statut="Annulé")
    _vente(conn, "B4", "2026-11-03", 2, 777, 0)  # autre vendeur
    conn.commit()

    s = vd.situation_vendeur(conn, 1)
    assert s["nb_ventes"] == 2
    assert s["ca"] == 1500
    assert s["credit_accorde"] == 600


def test_encaissement_somme_des_versements_sans_double_comptage(conn):
    # Vente avec 400 versés + le versement correspondant (comme l'API terrain)
    _vente(conn, "B1", "2026-11-02", 1, 1000, 400)
    _vers(conn, "versements_clients", "VR1", "2026-11-02", 1, 400)
    _vers(conn, "versements_prospects", "VR2", "2026-11-03", 1, 250, mode="Chèque")
    _vers(conn, "versements_clients", "VR3", "2026-11-03", 2, 999)  # autre vendeur
    conn.commit()

    s = vd.situation_vendeur(conn, 1)
    assert s["encaisse_total"] == 650          # 400 + 250, pas 400 + 400 + 250
    assert s["encaisse_especes"] == 400
    assert s["nb_versements"] == 2

    liste = vd.versements_vendeur(conn, 1)
    assert [v["numero"] for v in liste] == ["VR2", "VR1"]
    assert {v["type"] for v in liste} == {"Client", "Prospect"}


def test_filtre_par_periode(conn):
    _vente(conn, "B1", "2026-10-15", 1, 100, 0)
    _vente(conn, "B2", "2026-11-05", 1, 200, 0)
    conn.commit()
    s = vd.situation_vendeur(conn, 1, "2026-11-01", "2026-11-30")
    assert s["nb_ventes"] == 1 and s["ca"] == 200
    assert len(vd.ventes_vendeur(conn, 1, "2026-11-01", None)) == 1
    assert len(vd.ventes_vendeur(conn, 1)) == 2


def test_chargement_stock_camion_et_valeur(conn):
    bon = creer_bon_chargement(conn, 1, [(1, 3)], "matin")
    creer_bon_chargement(conn, 2, [(1, 1)], "autre")

    chg = vd.chargements_vendeur(conn, 1)
    assert len(chg) == 1 and chg[0]["numero"] == bon["numero"]
    lignes = vd.lignes_chargement(conn, chg[0]["id"])
    assert lignes[0]["quantite_colis"] == 3 and lignes[0]["quantite_pieces"] == 30

    camion = vd.stock_camion(conn, 1)
    assert len(camion) == 1 and camion[0]["quantite_pieces"] == 30
    assert camion[0]["valeur"] == 3000

    s = vd.situation_vendeur(conn, 1)
    assert s["nb_chargements"] == 1
    assert s["colis_charges"] == 3
    assert s["camion_valeur"] == 3000


def test_prospects_et_conversion(conn):
    assert [p["code"] for p in vd.prospects_vendeur(conn, 1)] == ["PR1"]
    s = vd.situation_vendeur(conn, 1)
    assert s["nb_prospects"] == 1 and s["prospects_convertis"] == 0

    res = vd.convertir_prospect_en_client(conn, 1)
    assert res["code"].startswith("CLT-")
    assert vd.prospects_vendeur(conn, 1)[0]["statut"] == "Converti"
    assert vd.situation_vendeur(conn, 1)["prospects_convertis"] == 1

    with pytest.raises(ValueError):
        vd.convertir_prospect_en_client(conn, 1)  # déjà converti
    with pytest.raises(ValueError):
        vd.convertir_prospect_en_client(conn, 999)


def test_commandes_et_pointages(conn):
    conn.execute(
        """INSERT INTO commandes_clients(numero, client_id, vendeur_id, date_commande, statut, total_estime)
           VALUES('CC1', 1, 1, '2026-11-02', 'En attente', 300)""")
    conn.execute(
        """INSERT INTO commandes_prospects(numero, prospect_id, vendeur_id, date_commande, statut, montant_total)
           VALUES('CP1', 1, 1, '2026-11-03', 'Validée', 150)""")
    conn.execute(
        """INSERT INTO tournee_pointages(client_id, vendeur_id, code_client, nom_client, date_pointage)
           VALUES(1, 1, 'C1', 'Client Un', '2026-11-03T09:00:00')""")
    conn.commit()

    cmds = vd.commandes_vendeur(conn, 1)
    assert [c["numero"] for c in cmds] == ["CP1", "CC1"]
    assert vd.situation_vendeur(conn, 1)["commandes_en_attente"] == 1
    assert len(vd.pointages_vendeur(conn, 1)) == 1
    assert vd.situation_vendeur(conn, 1)["nb_pointages"] == 1
    assert vd.pointages_vendeur(conn, 2) == []
