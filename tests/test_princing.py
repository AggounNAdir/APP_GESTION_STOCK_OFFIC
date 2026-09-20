"""
Tests du service unique de tarification (api/princing.py).
Base SQLite en mémoire : ne touche pas à api/gestion_stock.db.
"""
import sqlite3
from datetime import date, timedelta

import pytest

from api import princing as P


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        CREATE TABLE produits (
            id INTEGER PRIMARY KEY, prix_achat REAL, prix_vente REAL,
            prix_moyen_pondere REAL DEFAULT 0,
            prix_super_gros REAL DEFAULT 0, prix_gros REAL DEFAULT 0,
            prix_detail REAL DEFAULT 0, prix_special REAL DEFAULT 0
        );
        CREATE TABLE clients (id INTEGER PRIMARY KEY, niveau_prix TEXT DEFAULT 'detail');
        CREATE TABLE clients_niveau_prix (client_id INTEGER PRIMARY KEY, niveau TEXT);
        CREATE TABLE prix_speciaux_clients (
            id INTEGER PRIMARY KEY, client_id INTEGER, produit_id INTEGER,
            prix_special REAL, date_debut TEXT, date_fin TEXT, actif INTEGER DEFAULT 1,
            UNIQUE(client_id, produit_id)
        );
        CREATE TABLE prix_paliers (
            id INTEGER PRIMARY KEY, produit_id INTEGER, niveau TEXT,
            qte_min REAL, prix REAL, actif INTEGER DEFAULT 1,
            UNIQUE(produit_id, niveau, qte_min)   -- comme api/schema.py
        );
        -- produit 1 : 4 niveaux renseignés, coût 70
        INSERT INTO produits VALUES (1, 70, 120, 0, 90, 100, 120, 110);
        -- produit 2 : seul prix_vente renseigné (colonnes de niveau à 0)
        INSERT INTO produits VALUES (2, 50, 80, 0, 0, 0, 0, 0);
        -- produit 3 : prix moyen pondéré prioritaire sur prix_achat
        INSERT INTO produits VALUES (3, 10, 20, 15, 0, 0, 20, 0);
        INSERT INTO clients (id) VALUES (1), (2), (3), (4);
        INSERT INTO clients_niveau_prix VALUES (1, 'super_gros'), (2, 'gros');
        """
    )
    yield c
    c.close()


# ── niveau du client ──────────────────────────────────────────────────────

def test_niveau_depuis_table(conn):
    assert P.get_niveau_client(conn, 1) == "super_gros"
    assert P.get_niveau_client(conn, 2) == "gros"


def test_niveau_repli_sur_colonne_client(conn):
    conn.execute("UPDATE clients SET niveau_prix='gros' WHERE id=3")
    assert P.get_niveau_client(conn, 3) == "gros"


def test_niveau_inconnu_ou_absent_donne_detail(conn):
    assert P.get_niveau_client(conn, None) == "detail"
    assert P.get_niveau_client(conn, 4) == "detail"
    conn.execute("INSERT INTO clients_niveau_prix VALUES (4, 'vip_bidon')")
    assert P.get_niveau_client(conn, 4) == "detail"


# ── prix par niveau ───────────────────────────────────────────────────────

@pytest.mark.parametrize("client_id,attendu", [(1, 90), (2, 100), (4, 120), (None, 120)])
def test_prix_selon_niveau(conn, client_id, attendu):
    r = P.resoudre_prix(conn, 1, client_id=client_id)
    assert r.prix == attendu
    assert r.source == P.SOURCE_NIVEAU


def test_repli_prix_vente_si_niveau_a_zero(conn):
    r = P.resoudre_prix(conn, 2, client_id=1)  # super_gros = 0 → prix_vente
    assert r.prix == 80
    assert r.source == P.SOURCE_PRIX_VENTE


def test_produit_introuvable(conn):
    r = P.resoudre_prix(conn, 999, client_id=1)
    assert r.prix == 0 and r.source == P.SOURCE_INTROUVABLE


def test_niveau_force_manuel_ignore_le_client(conn):
    r = P.resoudre_prix(conn, 1, client_id=1, niveau="detail")
    assert r.prix == 120  # le client est super_gros, mais le vendeur a cliqué « détail »


# ── prix spécial client + dates ───────────────────────────────────────────

def _special(conn, client, produit, prix, debut=None, fin=None, actif=1):
    conn.execute(
        "INSERT INTO prix_speciaux_clients(client_id,produit_id,prix_special,date_debut,date_fin,actif)"
        " VALUES (?,?,?,?,?,?)", (client, produit, prix, debut, fin, actif))


def test_special_client_gagne_sur_le_niveau(conn):
    _special(conn, 1, 1, 85)
    r = P.resoudre_prix(conn, 1, client_id=1)
    assert (r.prix, r.source) == (85, P.SOURCE_SPECIAL_CLIENT)


def test_special_ne_s_applique_qu_a_son_client(conn):
    _special(conn, 1, 1, 85)
    assert P.resoudre_prix(conn, 1, client_id=2).prix == 100


def test_special_expire_est_ignore(conn):
    hier = (date.today() - timedelta(days=1)).isoformat()
    _special(conn, 1, 1, 85, fin=hier)
    assert P.resoudre_prix(conn, 1, client_id=1).prix == 90


def test_special_pas_encore_valide_est_ignore(conn):
    demain = (date.today() + timedelta(days=1)).isoformat()
    _special(conn, 1, 1, 85, debut=demain)
    assert P.resoudre_prix(conn, 1, client_id=1).prix == 90


def test_special_dans_sa_periode_et_dates_vides(conn):
    hier = (date.today() - timedelta(days=1)).isoformat()
    demain = (date.today() + timedelta(days=1)).isoformat()
    _special(conn, 1, 1, 85, debut=hier, fin=demain)
    assert P.resoudre_prix(conn, 1, client_id=1).prix == 85
    conn.execute("DELETE FROM prix_speciaux_clients")
    _special(conn, 1, 1, 86, debut="", fin="")
    assert P.resoudre_prix(conn, 1, client_id=1).prix == 86


def test_special_inactif_ou_nul_est_ignore(conn):
    _special(conn, 1, 1, 85, actif=0)
    assert P.resoudre_prix(conn, 1, client_id=1).prix == 90
    conn.execute("DELETE FROM prix_speciaux_clients")
    _special(conn, 1, 1, 0)
    assert P.resoudre_prix(conn, 1, client_id=1).prix == 90


def test_jour_de_reference_explicite(conn):
    _special(conn, 1, 1, 85, fin="2020-01-31")
    assert P.resoudre_prix(conn, 1, client_id=1, jour="2020-01-15").prix == 85
    assert P.resoudre_prix(conn, 1, client_id=1, jour="2020-02-01").prix == 90


# ── paliers de quantité ───────────────────────────────────────────────────

def _paliers(conn):
    conn.executemany(
        "INSERT INTO prix_paliers(produit_id,niveau,qte_min,prix) VALUES (?,?,?,?)",
        [(1, "gros", 10, 95), (1, "gros", 50, 92), (1, "super_gros", 100, 85)])


def test_palier_choisit_le_plus_haut_atteint(conn):
    _paliers(conn)
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=5).prix == 100    # sous 10 : niveau
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=10).prix == 95
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=49).prix == 95
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=50).prix == 92
    r = P.resoudre_prix(conn, 1, client_id=2, quantite=500)
    assert (r.source, r.qte_min) == (P.SOURCE_PALIER, 50)


def test_palier_propre_a_son_niveau(conn):
    _paliers(conn)
    # client 2 (gros) n'a pas droit au palier super_gros
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=100).prix == 92
    # client 1 (super_gros) : palier 85 à partir de 100
    assert P.resoudre_prix(conn, 1, client_id=1, quantite=100).prix == 85
    assert P.resoudre_prix(conn, 1, client_id=1, quantite=99).prix == 90


def test_special_client_bat_le_palier(conn):
    _paliers(conn)
    _special(conn, 2, 1, 99)
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=500).prix == 99


def test_sans_quantite_les_paliers_sont_ignores(conn):
    _paliers(conn)
    assert P.resoudre_prix(conn, 1, client_id=2).prix == 100


def test_table_paliers_absente_ne_plante_pas(conn):
    conn.execute("DROP TABLE prix_paliers")
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=500).prix == 100


def test_resolve_prix_compat(conn):
    assert P.resolve_prix(conn, 2, 1) == 100  # ancienne signature (client, produit)


# ── marge ─────────────────────────────────────────────────────────────────

def test_marge_ok(conn):
    m = P.verifier_marge(conn, 1, 100)  # coût 70
    assert m.ok and m.statut == P.STATUT_OK
    assert round(m.marge_pct, 2) == 42.86


def test_vente_sous_le_cout(conn):
    m = P.verifier_marge(conn, 1, 60)
    assert not m.ok and m.statut == P.STATUT_SOUS_COUT
    assert "perte" in m.message


def test_marge_minimale(conn):
    assert P.verifier_marge(conn, 1, 75, marge_min_pct=10).statut == P.STATUT_SOUS_MARGE
    assert P.verifier_marge(conn, 1, 80, marge_min_pct=10).ok


def test_cout_prend_le_prix_moyen_pondere(conn):
    assert P.cout_produit(conn, 3) == 15   # pmp (15) prioritaire sur prix_achat (10)
    assert P.cout_produit(conn, 1) == 70   # pas de pmp → prix_achat


def test_cout_inconnu_n_est_pas_bloquant(conn):
    conn.execute("UPDATE produits SET prix_achat=0 WHERE id=1")
    m = P.verifier_marge(conn, 1, 1)
    assert m.ok and m.statut == P.STATUT_COUT_INCONNU


def test_marge_min_depuis_environnement(conn, monkeypatch):
    monkeypatch.setenv("PRIX_MARGE_MIN_PCT", "20")
    assert P.verifier_marge(conn, 1, 80).statut == P.STATUT_SOUS_MARGE  # +14 %
    monkeypatch.setenv("PRIX_MARGE_MIN_PCT", "abc")
    assert P.verifier_marge(conn, 1, 80).ok


# ── contrôle des commandes ────────────────────────────────────────────────

def _ligne(pid, qte, prix, facteur=1):
    return {"produit_id": pid, "quantite": qte, "prix_unitaire": prix, "facteur_conversion": facteur}


def test_portail_prix_trop_bas_bloquant_en_enforce(conn):
    an = P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 80)], est_vendeur=False, mode="enforce")
    assert an and an[0].bloquant


def test_portail_prix_correct_ou_superieur_ok(conn):
    lignes = [_ligne(1, 1, 100), _ligne(1, 1, 130)]
    assert P.controler_lignes_commande(conn, 2, lignes, False, mode="enforce") == []


def test_warn_ne_bloque_jamais(conn):
    an = P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 80)], est_vendeur=False, mode="warn")
    assert an and not any(a.bloquant for a in an)


def test_off_ne_controle_rien(conn):
    assert P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 1)], False, mode="off") == []


def test_vendeur_peut_negocier_sous_le_tarif_mais_pas_sous_le_cout(conn):
    # 95 < tarif gros (100) mais > coût (70) : autorisé pour un vendeur
    assert P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 95)], True, mode="enforce") == []
    an = P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 60)], True, mode="enforce")
    assert an and an[0].bloquant


def test_prospect_seule_la_marge_est_controlee(conn):
    assert P.controler_lignes_commande(conn, None, [_ligne(1, 1, 75)], True, mode="enforce") == []
    assert P.controler_lignes_commande(conn, None, [_ligne(1, 1, 60)], True, mode="enforce")


def test_ligne_sans_prix_est_ignoree(conn):
    assert P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 0)], False, mode="enforce") == []


def test_controle_utilise_les_paliers_avec_le_facteur(conn):
    _paliers(conn)
    # 5 cartons × 12 = 60 unités → palier gros ≥ 50 → tarif attendu 92 ; 93 est correct
    assert P.controler_lignes_commande(conn, 2, [_ligne(1, 5, 93, facteur=12)], False, mode="enforce") == []
    # 1 carton × 12 = 12 unités → palier ≥ 10 → 95 attendu ; 93 est trop bas
    assert P.controler_lignes_commande(conn, 2, [_ligne(1, 1, 93, facteur=12)], False, mode="enforce")


def test_accepte_les_objets_pydantic(conn):
    from types import SimpleNamespace
    item = SimpleNamespace(produit_id=1, quantite=1, prix_unitaire=80, facteur_conversion=1)
    assert P.controler_lignes_commande(conn, 2, [item], False, mode="enforce")


# ── paliers : normalisation, lecture, écriture, validation ────────────────

def test_normaliser_paliers_nettoie_dedoublonne_et_trie():
    brut = [
        {"niveau": "gros", "qte_min": 50, "prix": 92},
        {"niveau": "GROS", "qte_min": 10, "prix": 95},          # majuscules acceptées
        {"niveau": "gros", "qte_min": 50, "prix": 91},          # doublon : le dernier gagne
        {"niveau": "vip", "qte_min": 5, "prix": 80},            # niveau inconnu : ignoré
        {"niveau": "detail", "qte_min": 0, "prix": 80},         # quantité nulle : ignoré
        {"niveau": "detail", "qte_min": 5, "prix": 0},          # prix nul : ignoré
        {"niveau": "super_gros", "qte_min": 100, "prix": 85},
    ]
    assert P.normaliser_paliers(brut) == [
        {"niveau": "super_gros", "qte_min": 100.0, "prix": 85.0},
        {"niveau": "gros", "qte_min": 10.0, "prix": 95.0},
        {"niveau": "gros", "qte_min": 50.0, "prix": 91.0},
    ]


def test_ecrire_puis_lire_les_paliers(conn):
    n = P.enregistrer_paliers(conn, 1, [
        {"niveau": "gros", "qte_min": 10, "prix": 95},
        {"niveau": "gros", "qte_min": 50, "prix": 92}])
    assert n == 2
    assert [(p["niveau"], p["qte_min"], p["prix"]) for p in P.lire_paliers(conn, 1)] == \
        [("gros", 10.0, 95.0), ("gros", 50.0, 92.0)]
    # et le calcul de prix les utilise aussitôt
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=60).prix == 92


def test_enregistrer_remplace_modifie_et_supprime(conn):
    P.enregistrer_paliers(conn, 1, [{"niveau": "gros", "qte_min": 10, "prix": 95},
                                    {"niveau": "gros", "qte_min": 50, "prix": 92}])
    # on change le prix du palier 10, on supprime le palier 50, on en ajoute un autre niveau
    P.enregistrer_paliers(conn, 1, [{"niveau": "gros", "qte_min": 10, "prix": 96},
                                    {"niveau": "detail", "qte_min": 20, "prix": 110}])
    assert [(p["niveau"], p["qte_min"], p["prix"]) for p in P.lire_paliers(conn, 1)] == \
        [("gros", 10.0, 96.0), ("detail", 20.0, 110.0)]


def test_enregistrer_liste_vide_supprime_tout_et_ne_touche_pas_un_autre_produit(conn):
    P.enregistrer_paliers(conn, 1, [{"niveau": "gros", "qte_min": 10, "prix": 95}])
    P.enregistrer_paliers(conn, 2, [{"niveau": "gros", "qte_min": 10, "prix": 70}])
    P.enregistrer_paliers(conn, 1, [])
    assert P.lire_paliers(conn, 1) == []
    assert len(P.lire_paliers(conn, 2)) == 1


def test_enregistrer_respecte_les_paliers_desactives(conn):
    conn.execute("INSERT INTO prix_paliers(produit_id,niveau,qte_min,prix,actif) VALUES (1,'gros',200,80,0)")
    P.enregistrer_paliers(conn, 1, [{"niveau": "gros", "qte_min": 10, "prix": 95}])
    assert conn.execute("SELECT COUNT(*) FROM prix_paliers WHERE actif=0").fetchone()[0] == 1
    assert P.resoudre_prix(conn, 1, client_id=2, quantite=500).prix == 95  # le désactivé est ignoré


def test_lire_paliers_table_absente(conn):
    conn.execute("DROP TABLE prix_paliers")
    assert P.lire_paliers(conn, 1) == []


def test_valider_palier_erreurs():
    assert P.valider_palier("vip", 10, 90)[0]
    assert P.valider_palier("gros", 0, 90)[0]
    assert P.valider_palier("gros", 10, 0)[0]
    assert P.valider_palier("gros", 10, 90) == (None, [])


def test_valider_palier_avertissements():
    err, av = P.valider_palier("gros", 10, 110, prix_niveau=100)
    assert err is None and len(av) == 1 and "SUPÉRIEUR" in av[0]
    # sous le prix d'achat : REFUSÉ (erreur), plus un simple avertissement
    err, av = P.valider_palier("gros", 10, 60, prix_niveau=100, cout=70)
    assert err and "prix d'achat" in err and av == []
    # égal au prix d'achat : accepté
    assert P.valider_palier("gros", 10, 70, prix_niveau=100, cout=70) == (None, [])
    # coût inconnu (0) : pas de contrôle
    assert P.valider_palier("gros", 10, 60, prix_niveau=100, cout=0) == (None, [])
    err, av = P.valider_palier("gros", 10, 95, prix_niveau=100, cout=70)
    assert (err, av) == (None, [])


def test_coherence_paliers():
    ok = [{"niveau": "gros", "qte_min": 10, "prix": 95}, {"niveau": "gros", "qte_min": 50, "prix": 92}]
    assert P.verifier_coherence_paliers(ok) == []
    # même prix : accepté ; niveaux différents : comparés séparément
    egal = ok + [{"niveau": "gros", "qte_min": 100, "prix": 92}, {"niveau": "detail", "qte_min": 5, "prix": 200}]
    assert P.verifier_coherence_paliers(egal) == []
    ko = [{"niveau": "gros", "qte_min": 10, "prix": 92}, {"niveau": "gros", "qte_min": 50, "prix": 95}]
    av = P.verifier_coherence_paliers(ko)
    assert len(av) == 1 and "plus cher" in av[0] and "GROS" in av[0]


# ── prix de vente par défaut / alerte « prix Détail vide » ────────────────

def test_prix_vente_defaut():
    assert P.prix_vente_defaut(100, 150) == 150            # le prix Détail saisi gagne
    assert P.prix_vente_defaut(100, 0) == pytest.approx(135)   # sinon achat + 35 %
    assert P.prix_vente_defaut(100, "") == pytest.approx(135)
    assert P.prix_vente_defaut(0, 0) == 0
    assert P.prix_vente_defaut(None, None) == 0


def test_pas_d_alerte_si_prix_detail_saisi():
    assert P.avertissement_prix_detail(100, 150) is None
    assert P.avertissement_prix_detail(0, 150) is None     # achat inconnu mais Détail saisi


def test_alerte_detail_vide_avec_prix_achat():
    msg = P.avertissement_prix_detail(100, 0)
    assert msg and "Détail est vide" in msg and "135.00" in msg


def test_alerte_detail_vide_sans_prix_achat():
    msg = P.avertissement_prix_detail(0, "")
    assert msg and "impossible à vendre" in msg


# ── aucun prix de vente sous le prix d'achat (fiche produit) ──────────────

def test_prix_sous_le_cout_accepte_les_prix_valides():
    niveaux = {"super_gros": 105, "gros": 110, "detail": 135, "special": 100}   # 100 = égal au coût : accepté
    assert P.prix_sous_le_cout(100, niveaux) == []


def test_prix_sous_le_cout_refuse_chaque_niveau_fautif():
    err = P.prix_sous_le_cout(100, {"super_gros": 90, "gros": 110, "detail": 99.99, "special": 0})
    assert len(err) == 2
    assert "Super Gros" in err[0] and "90.00" in err[0] and "100.00" in err[0]
    assert "Détail" in err[1]


def test_prix_sous_le_cout_ignore_les_niveaux_vides():
    assert P.prix_sous_le_cout(100, {"super_gros": "", "gros": 0, "detail": None}) == []


def test_prix_sous_le_cout_sans_prix_d_achat_ne_controle_rien():
    assert P.prix_sous_le_cout(0, {"detail": 1}) == []
    assert P.prix_sous_le_cout("", {"detail": 1}) == []


def test_prix_sous_le_cout_controle_aussi_les_paliers():
    paliers = [{"niveau": "gros", "qte_min": 50, "prix": 95},
               {"niveau": "gros", "qte_min": 100, "prix": 100}]      # égal au coût : accepté
    err = P.prix_sous_le_cout(100, {"detail": 135}, paliers)
    assert len(err) == 1 and "Palier Gros" in err[0] and "50" in err[0]


def test_prix_sous_le_cout_arrondi_au_centime():
    assert P.prix_sous_le_cout(100, {"detail": 99.996}) == []     # arrondi à 100.00 : pas de faux refus
