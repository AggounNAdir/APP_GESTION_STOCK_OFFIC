import sqlite3

import pytest

from api import vendeur_dossier as vd
from api.schema import init_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    c.execute("INSERT INTO vendeurs(code, nom, actif) VALUES('V1', 'Ali', 1)")
    c.execute("INSERT INTO vendeurs(code, nom, actif) VALUES('V2', 'Omar', 1)")
    c.execute("INSERT INTO clients(code, nom) VALUES('C1', 'Client Un')")
    c.commit()
    yield c
    c.close()


def _vers(c, num, date, vendeur, montant, mode="Espèces"):
    c.execute(
        """INSERT INTO versements_clients(numero, date_vers, client_id, montant, mode, vendeur_id)
           VALUES(?,?,1,?,?,?)""", (num, date, montant, mode, vendeur))
    c.commit()


def test_reste_a_verser_et_remise(conn):
    _vers(conn, "VC1", "2026-11-10", 1, 10000)
    _vers(conn, "VC2", "2026-11-11", 1, 5000)
    _vers(conn, "VC3", "2026-11-11", 1, 3000, mode="Virement")  # pas de cash
    _vers(conn, "VC4", "2026-11-11", 2, 9999)                   # autre vendeur
    assert vd.caisse_vendeur(conn, 1)["reste_a_verser"] == 15000

    r = vd.creer_versement_admin(conn, 1, 6000, date_vers="2026-11-11")
    assert r["numero"] == "VV202611-0001" and r["reste_a_verser"] == 9000
    c = vd.caisse_vendeur(conn, 1)
    assert c["reste_a_verser"] == 9000 and c["cumul_verse_admin"] == 6000
    assert vd.caisse_vendeur(conn, 2)["reste_a_verser"] == 9999


def test_solde_cumule_independant_de_la_periode(conn):
    _vers(conn, "VC1", "2026-11-01", 1, 4000)
    c = vd.caisse_vendeur(conn, 1, "2026-11-12", "2026-11-12")
    assert c["periode_encaisse_especes"] == 0
    assert c["reste_a_verser"] == 4000


def test_depassement_refuse_sauf_autorisation(conn):
    _vers(conn, "VC1", "2026-11-10", 1, 1000)
    with pytest.raises(ValueError):
        vd.creer_versement_admin(conn, 1, 1500)
    vd.creer_versement_admin(conn, 1, 1500, autoriser_depassement=True)
    assert vd.caisse_vendeur(conn, 1)["reste_a_verser"] == -500


@pytest.mark.parametrize("m", [0, -5, "abc", None])
def test_montant_invalide(conn, m):
    with pytest.raises(ValueError):
        vd.creer_versement_admin(conn, 1, m)


def test_annulation_reintegre_le_solde(conn):
    _vers(conn, "VC1", "2026-11-10", 1, 2000)
    r = vd.creer_versement_admin(conn, 1, 2000)
    assert vd.caisse_vendeur(conn, 1)["reste_a_verser"] == 0
    vd.annuler_versement_admin(conn, r["id"])
    assert vd.caisse_vendeur(conn, 1)["reste_a_verser"] == 2000
    with pytest.raises(ValueError):
        vd.annuler_versement_admin(conn, r["id"])
    assert len(vd.versements_admin_vendeur(conn, 1)) == 1  # historique conservé


def test_numeros_sequentiels(conn):
    _vers(conn, "VC1", "2026-11-10", 1, 9000)
    a = vd.creer_versement_admin(conn, 1, 100, date_vers="2026-11-10")
    b = vd.creer_versement_admin(conn, 1, 100, date_vers="2026-11-10")
    assert (a["numero"], b["numero"]) == ("VV202611-0001", "VV202611-0002")


def test_creances_baissent_apres_versement_du_prospect(conn):
    conn.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut, solde)
           VALUES('P9', 'Prospect Neuf', NULL, '2026-11-02T10:00:00', 'Nouveau', 1000)""")
    pid = conn.execute("SELECT id FROM prospects_clients WHERE code='P9'").fetchone()[0]
    conn.execute(
        """INSERT INTO bons_vente(numero, date_bon, client_id, prospect_id, vendeur_id, total,
                                  montant_verse, reste_payer, statut)
           VALUES('BV-TERRAIN-1', '2026-11-10', 1, ?, 1, 1000, 0, 1000, 'Validé')""", (pid,))
    conn.commit()
    c = vd.caisse_vendeur(conn, 1)
    assert c["creances_clients"] == 1000 and c["periode_credit"] == 1000

    # Le prospect verse 400 plus tard (même écriture que POST /versements)
    conn.execute(
        """INSERT INTO versements_prospects(numero, date_vers, prospect_id, vendeur_id, montant, mode)
           VALUES('VP-1', '2026-11-12', ?, 1, 400, 'Espèces')""", (pid,))
    conn.execute("UPDATE prospects_clients SET solde = MAX(0, solde - 400) WHERE id=?", (pid,))
    conn.commit()
    c = vd.caisse_vendeur(conn, 1)
    assert c["creances_clients"] == 600          # reste dû : baisse
    assert c["periode_credit"] == 1000           # crédit accordé à la vente : historique
    assert c["reste_a_verser"] == 400            # les 400 DA sont à remettre à l'administration


def test_credit_en_cours_monte_avec_nouvelle_vente_et_baisse_avec_versement(conn):
    conn.execute(
        """INSERT INTO prospects_clients(code, nom, vendeur_id, date_creation, statut, solde)
           VALUES('P8', 'Prospect Huit', 1, '2026-11-01T10:00:00', 'Nouveau', 0)""")
    pid = conn.execute("SELECT id FROM prospects_clients WHERE code='P8'").fetchone()[0]

    def vente(num, reste):  # même effet que POST /tournee/vente-directe
        conn.execute(
            """INSERT INTO bons_vente(numero, date_bon, client_id, prospect_id, vendeur_id,
                                      total, montant_verse, reste_payer, statut)
               VALUES(?, '2026-11-12', 1, ?, 1, ?, 0, ?, 'Validé')""", (num, pid, reste, reste))
        conn.execute("UPDATE prospects_clients SET solde = solde + ? WHERE id=?", (reste, pid))
        conn.commit()

    vente("BV-TERRAIN-A", 1000)
    assert vd.caisse_vendeur(conn, 1)["creances_clients"] == 1000
    vente("BV-TERRAIN-B", 500)                       # nouveau crédit
    assert vd.caisse_vendeur(conn, 1)["creances_clients"] == 1500
    conn.execute("UPDATE prospects_clients SET solde = solde - 700 WHERE id=?", (pid,))
    conn.commit()                                    # versement du prospect
    assert vd.caisse_vendeur(conn, 1)["creances_clients"] == 800