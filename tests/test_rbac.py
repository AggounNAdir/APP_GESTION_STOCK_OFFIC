"""
Tests du système d'utilisateurs, rôles et journal d'audit (api/rbac.py).

Tout s'exécute sur une base SQLite EN MÉMOIRE créée avec le schéma réel
(api/schema.init_schema) : aucune dépendance à la vraie base.

    python -m pytest tests/test_rbac.py
"""
import sqlite3

import pytest

from api import rbac
from api.schema import init_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)          # crée aussi le compte admin/admin123 par défaut
    yield c
    c.close()


@pytest.fixture(autouse=True)
def _reset_session():
    """Le rôle/session courants sont un état global (api.rbac) : on l'isole
    entre les tests pour éviter qu'un test en pollue un autre."""
    rbac.set_utilisateur_connecte(None)
    yield
    rbac.set_utilisateur_connecte(None)


def _audit(conn, pid=None):
    sql = "SELECT * FROM journal_audit"
    args = ()
    if pid is not None:
        sql += " WHERE cible_id=?"
        args = (pid,)
    return conn.execute(sql + " ORDER BY id", args).fetchall()


# ═══════════════════════════ SCHÉMA / BOOTSTRAP ═══════════════════════════

def test_tables_et_index_crees(conn):
    noms = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert {"utilisateurs", "journal_audit", "idx_utilisateurs_role",
            "idx_audit_date", "idx_audit_utilisateur", "idx_audit_action"} <= noms


def test_bootstrap_cree_admin_par_defaut(conn):
    admin = conn.execute("SELECT * FROM utilisateurs WHERE username='admin'").fetchone()
    assert admin is not None
    assert admin["role"] == "admin" and admin["actif"] == 1 and admin["doit_changer_mdp"] == 1
    assert rbac.authentifier(conn, "admin", "admin123") is not None


def test_bootstrap_idempotent_ne_duplique_pas(conn):
    init_schema(conn)
    init_schema(conn)
    assert conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0] == 1


def test_bootstrap_sans_effet_si_compte_existe_deja(conn):
    # simulate a pre-existing account before rbac ran (defensive check)
    nb_avant = conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
    assert nb_avant == 1
    assert rbac.bootstrap_admin_par_defaut(conn) is None


def test_journal_audit_en_ajout_seul(conn):
    rbac.ajouter_audit(conn, "CONNEXION", utilisateur="admin")
    with pytest.raises(sqlite3.IntegrityError, match="lecture seule"):
        conn.execute("UPDATE journal_audit SET action='X'")
    with pytest.raises(sqlite3.IntegrityError, match="lecture seule"):
        conn.execute("DELETE FROM journal_audit")


# ═══════════════════════════ RÔLES / CATÉGORIES ═══════════════════════════

def test_admin_voit_tout():
    for page in rbac.PAGE_CATEGORIE:
        assert rbac.peut_voir_page("admin", page)


def test_gestionnaire_ne_voit_pas_utilisateurs():
    assert not rbac.peut_voir_page("gestionnaire", "utilisateurs")


def test_page_retours_unifiee_visible_si_un_type_est_autorise():
    assert rbac.peut_voir_page("vendeur", "retours")
    assert rbac.peut_voir_page("caissier", "retours")
    assert rbac.peut_voir_page("gestionnaire", "retours")
    assert not rbac.peut_voir_page(None, "retours")


@pytest.mark.parametrize("role", list(rbac.ROLE_CATEGORIES))
def test_situations_unifiees_conservent_les_droits_finances(role):
    assert rbac.peut_voir_page(role, "situations") == rbac.peut_voir_page(role, "sit_clients")
    assert rbac.peut_voir_page(role, "situations") == rbac.peut_voir_page(role, "sit_fourn")


@pytest.mark.parametrize("role", list(rbac.ROLE_CATEGORIES))
def test_statistiques_unifiees_conservent_les_droits_rapports(role):
    assert rbac.peut_voir_page(role, "statistiques") == rbac.peut_voir_page(role, "stats_achats")
    assert rbac.peut_voir_page(role, "statistiques") == rbac.peut_voir_page(role, "stats_ventes")
    assert rbac.peut_voir_page(role, "statistiques") == rbac.peut_voir_page(role, "analyse_produits")


@pytest.mark.parametrize("role", list(rbac.ROLE_CATEGORIES))
def test_versements_unifies_conservent_les_droits_finances(role):
    assert rbac.peut_voir_page(role, "versements") == rbac.peut_voir_page(role, "vers_clients")
    assert rbac.peut_voir_page(role, "versements") == rbac.peut_voir_page(role, "vers_fourn")
    assert not rbac.peut_voir_page("gestionnaire", "journal_audit")
    assert rbac.peut_voir_page("gestionnaire", "bons_achat")


def test_vendeur_restreint_aux_ventes():
    assert rbac.peut_voir_page("vendeur", "bons_vente")
    assert rbac.peut_voir_page("vendeur", "clients")
    assert not rbac.peut_voir_page("vendeur", "bons_achat")
    assert not rbac.peut_voir_page("vendeur", "mouvements_stock")
    assert not rbac.peut_voir_page("vendeur", "utilisateurs")


def test_caissier_tres_restreint():
    assert rbac.peut_voir_page("caissier", "bons_vente")
    assert not rbac.peut_voir_page("caissier", "produits")
    assert not rbac.peut_voir_page("caissier", "clients")
    assert not rbac.peut_voir_page("caissier", "bons_achat")


def test_lecture_seule_voit_mais_ne_peut_rien_faire_de_sensible():
    assert rbac.peut_voir_page("lecture_seule", "mouvements_stock")
    assert rbac.peut_voir_page("lecture_seule", "bons_achat")
    assert not rbac.peut_voir_page("lecture_seule", "utilisateurs")
    for action in rbac.ACTIONS:
        assert not rbac.peut("lecture_seule", action)


def test_aucun_role_ne_donne_gerer_utilisateurs_sauf_admin():
    for role in rbac.ROLES:
        attendu = (role == "admin")
        assert rbac.peut(role, "gerer_utilisateurs") == attendu


def test_page_non_repertoriee_ouverte_par_defaut():
    assert rbac.peut_voir_page("caissier", "une_page_qui_nexiste_pas")


def test_role_ou_page_absent():
    assert not rbac.peut_voir_page(None, "dashboard")
    assert not rbac.peut_voir_page("", "dashboard")
    assert not rbac.peut(None, "gerer_utilisateurs")
    assert not rbac.peut("admin", "action_inconnue")


def test_libelles():
    assert rbac.libelle_role("admin") == "Administrateur"
    assert rbac.libelle_role("xxx") == "xxx"                 # repli gracieux
    assert rbac.libelle_categorie("stock") == "Mouvements et ajustements de stock"


# ═══════════════════════════ SESSION ═══════════════════════════

def test_session_par_defaut_vide():
    assert rbac.get_utilisateur_connecte() is None
    assert rbac.role_courant() is None
    assert not rbac.peut_voir_page_courant("dashboard")
    assert not rbac.peut_courant("gerer_utilisateurs")


def test_set_utilisateur_connecte_et_courant():
    rbac.set_utilisateur_connecte({"id": 1, "nom_complet": "Karim", "role": "admin"})
    assert rbac.role_courant() == "admin"
    assert rbac.peut_voir_page_courant("utilisateurs")
    assert rbac.peut_courant("gerer_utilisateurs")
    rbac.set_utilisateur_connecte(None)
    assert rbac.get_utilisateur_connecte() is None


def test_session_retourne_une_copie(conn):
    """Modifier le dict retourné ne doit pas modifier l'état de session."""
    rbac.set_utilisateur_connecte({"id": 1, "nom_complet": "Karim", "role": "vendeur"})
    u = rbac.get_utilisateur_connecte()
    u["role"] = "admin"
    assert rbac.role_courant() == "vendeur"


def test_set_utilisateur_connecte_propage_au_journal_stock(conn):
    """La session RBAC doit alimenter le nom d'utilisateur du journal des
    mouvements de stock (api/stock_journal), pas la session Windows."""
    from api import stock_journal as sj
    rbac.set_utilisateur_connecte({"id": 1, "nom_complet": "Amina Benali", "role": "admin"})
    try:
        assert sj.get_utilisateur_courant() == "Amina Benali"
    finally:
        sj.set_utilisateur_courant(None)


# ═══════════════════════════ AUTHENTIFICATION ═══════════════════════════

def test_authentifier_ok_et_mauvais_mdp(conn):
    assert rbac.authentifier(conn, "admin", "admin123") is not None
    assert rbac.authentifier(conn, "admin", "mauvais") is None


def test_authentifier_utilisateur_inconnu_ou_vide(conn):
    assert rbac.authentifier(conn, "fantome", "peu importe") is None
    assert rbac.authentifier(conn, "", "") is None
    assert rbac.authentifier(conn, "admin", "") is None
    assert rbac.authentifier(conn, "  ", "x") is None


def test_authentifier_compte_inactif_refuse(conn):
    conn.execute("UPDATE utilisateurs SET actif=0 WHERE username='admin'")
    assert rbac.authentifier(conn, "admin", "admin123") is None


def test_enregistrer_connexion_met_a_jour_la_date(conn):
    uid = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    avant = conn.execute("SELECT derniere_connexion FROM utilisateurs WHERE id=?", (uid,)).fetchone()[0]
    assert avant is None
    rbac.enregistrer_connexion(conn, uid)
    apres = conn.execute("SELECT derniere_connexion FROM utilisateurs WHERE id=?", (uid,)).fetchone()[0]
    assert apres is not None


# ═══════════════════════════ CRÉATION / MODIFICATION DE COMPTES ═══════════════════════════

def test_creer_utilisateur_ok_et_hash_different_du_clair(conn):
    uid = rbac.creer_utilisateur(conn, "kbenali", "Karim Benali", "motdepasse", "vendeur",
                                 cree_par="admin")
    row = conn.execute("SELECT * FROM utilisateurs WHERE id=?", (uid,)).fetchone()
    assert row["username"] == "kbenali" and row["role"] == "vendeur" and row["actif"] == 1
    assert row["doit_changer_mdp"] == 1
    assert row["password_hash"] != "motdepasse"
    assert rbac.authentifier(conn, "kbenali", "motdepasse") is not None
    audit = _audit(conn, uid)
    assert audit and audit[0]["action"] == "CREATION_UTILISATEUR"


def test_creer_utilisateur_champs_obligatoires(conn):
    with pytest.raises(ValueError, match="obligatoire"):
        rbac.creer_utilisateur(conn, "", "Nom", "motdepasse123", "vendeur")
    with pytest.raises(ValueError, match="obligatoire"):
        rbac.creer_utilisateur(conn, "user1", "  ", "motdepasse123", "vendeur")


def test_creer_utilisateur_role_invalide(conn):
    with pytest.raises(ValueError, match="Rôle inconnu"):
        rbac.creer_utilisateur(conn, "user1", "Nom", "motdepasse123", "superadmin")


def test_creer_utilisateur_mot_de_passe_trop_court(conn):
    with pytest.raises(ValueError, match="6 caractères"):
        rbac.creer_utilisateur(conn, "user1", "Nom", "abc", "vendeur")


def test_creer_utilisateur_nom_deja_pris(conn):
    with pytest.raises(ValueError, match="déjà utilisé"):
        rbac.creer_utilisateur(conn, "admin", "Un Autre", "motdepasse123", "vendeur")


def test_nom_utilisateur_disponible(conn):
    assert not rbac.nom_utilisateur_disponible(conn, "admin")
    assert rbac.nom_utilisateur_disponible(conn, "nouveau")
    uid = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    assert rbac.nom_utilisateur_disponible(conn, "admin", exclure_id=uid)


def test_modifier_utilisateur(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Ancien Nom", "motdepasse", "vendeur")
    rbac.modifier_utilisateur(conn, uid, nom_complet="Nouveau Nom", role="caissier",
                              modifie_par="admin")
    row = conn.execute("SELECT * FROM utilisateurs WHERE id=?", (uid,)).fetchone()
    assert row["nom_complet"] == "Nouveau Nom" and row["role"] == "caissier"
    assert _audit(conn, uid)[-1]["action"] == "MODIFICATION_UTILISATEUR"


def test_modifier_utilisateur_nom_vide_refuse(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Nom", "motdepasse", "vendeur")
    with pytest.raises(ValueError, match="obligatoire"):
        rbac.modifier_utilisateur(conn, uid, nom_complet="   ")


def test_modifier_utilisateur_sans_rien_a_changer_ne_fait_rien(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Nom", "motdepasse", "vendeur")
    nb_avant = len(_audit(conn, uid))
    rbac.modifier_utilisateur(conn, uid)      # ni nom_complet ni role
    assert len(_audit(conn, uid)) == nb_avant


def test_activer_desactiver_utilisateur(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Nom", "motdepasse", "vendeur")
    rbac.activer_utilisateur(conn, uid, False, modifie_par="admin")
    assert conn.execute("SELECT actif FROM utilisateurs WHERE id=?", (uid,)).fetchone()[0] == 0
    assert rbac.authentifier(conn, "vend1", "motdepasse") is None
    assert _audit(conn, uid)[-1]["action"] == "DESACTIVATION_UTILISATEUR"
    rbac.activer_utilisateur(conn, uid, True, modifie_par="admin")
    assert _audit(conn, uid)[-1]["action"] == "ACTIVATION_UTILISATEUR"
    assert rbac.authentifier(conn, "vend1", "motdepasse") is not None


def test_changer_mot_de_passe(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Nom", "ancien_mdp", "vendeur")
    rbac.changer_mot_de_passe(conn, uid, "nouveau_mdp", doit_changer_mdp=False,
                              modifie_par="vend1")
    assert rbac.authentifier(conn, "vend1", "ancien_mdp") is None
    assert rbac.authentifier(conn, "vend1", "nouveau_mdp") is not None
    row = conn.execute("SELECT doit_changer_mdp FROM utilisateurs WHERE id=?", (uid,)).fetchone()
    assert row[0] == 0
    assert _audit(conn, uid)[-1]["action"] == "CHANGEMENT_MOT_DE_PASSE"


def test_changer_mot_de_passe_trop_court(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Nom", "motdepasse", "vendeur")
    with pytest.raises(ValueError, match="6 caractères"):
        rbac.changer_mot_de_passe(conn, uid, "abc")


def test_lister_utilisateurs(conn):
    rbac.creer_utilisateur(conn, "vend1", "Vendeur Un", "motdepasse", "vendeur")
    rbac.creer_utilisateur(conn, "vend2", "Vendeur Deux", "motdepasse", "vendeur")
    rbac.activer_utilisateur(conn, conn.execute(
        "SELECT id FROM utilisateurs WHERE username='vend2'").fetchone()[0], False)
    tous = rbac.lister_utilisateurs(conn)
    actifs = rbac.lister_utilisateurs(conn, inclure_inactifs=False)
    assert len(tous) == 3 and len(actifs) == 2
    assert [u["nom_complet"] for u in tous] == sorted(u["nom_complet"] for u in tous)


# ═══════════════════════════ PROTECTION DU DERNIER ADMIN ═══════════════════════════

def test_impossible_de_desactiver_le_dernier_admin(conn):
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    with pytest.raises(ValueError, match="dernier compte Administrateur"):
        rbac.activer_utilisateur(conn, admin_id, False)
    assert conn.execute("SELECT actif FROM utilisateurs WHERE id=?", (admin_id,)).fetchone()[0] == 1


def test_impossible_de_retrograder_le_dernier_admin(conn):
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    with pytest.raises(ValueError, match="dernier compte Administrateur"):
        rbac.modifier_utilisateur(conn, admin_id, role="gestionnaire")
    assert conn.execute("SELECT role FROM utilisateurs WHERE id=?", (admin_id,)).fetchone()[0] == "admin"


def test_desactivation_possible_avec_un_second_admin(conn):
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    rbac.creer_utilisateur(conn, "admin2", "Second Admin", "motdepasse", "admin")
    rbac.activer_utilisateur(conn, admin_id, False)      # ne doit pas lever
    assert conn.execute("SELECT actif FROM utilisateurs WHERE id=?", (admin_id,)).fetchone()[0] == 0


def test_retrogradation_possible_avec_un_second_admin(conn):
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    rbac.creer_utilisateur(conn, "admin2", "Second Admin", "motdepasse", "admin")
    rbac.modifier_utilisateur(conn, admin_id, role="lecture_seule")
    assert conn.execute("SELECT role FROM utilisateurs WHERE id=?", (admin_id,)).fetchone()[0] == "lecture_seule"


def test_desactiver_un_admin_deja_inactif_ne_leve_pas(conn):
    """Un admin déjà désactivé n'est pas compté : le désactiver « à nouveau »
    (no-op) ne doit pas être bloqué par la protection du dernier admin."""
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    rbac.creer_utilisateur(conn, "admin2", "Second Admin", "motdepasse", "admin")
    admin2_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin2'").fetchone()[0]
    rbac.activer_utilisateur(conn, admin2_id, False)
    rbac.activer_utilisateur(conn, admin2_id, False)     # déjà inactif : no-op, pas d'erreur


def test_desactiver_role_non_admin_jamais_bloque(conn):
    uid = rbac.creer_utilisateur(conn, "vend1", "Nom", "motdepasse", "vendeur")
    rbac.activer_utilisateur(conn, uid, False)            # ne doit jamais lever
    assert conn.execute("SELECT actif FROM utilisateurs WHERE id=?", (uid,)).fetchone()[0] == 0


def test_modifier_seulement_le_nom_dun_admin_ne_declenche_pas_la_protection(conn):
    """Changer le nom complet sans toucher au rôle ne doit pas être bloqué,
    même si c'est le dernier admin."""
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    rbac.modifier_utilisateur(conn, admin_id, nom_complet="Nouveau Nom Admin")
    row = conn.execute("SELECT nom_complet, role FROM utilisateurs WHERE id=?", (admin_id,)).fetchone()
    assert row["nom_complet"] == "Nouveau Nom Admin" and row["role"] == "admin"


def test_remettre_admin_sur_un_admin_ne_declenche_pas_la_protection(conn):
    """role="admin" (aucun changement réel) sur le dernier admin ne doit pas lever."""
    admin_id = conn.execute("SELECT id FROM utilisateurs WHERE username='admin'").fetchone()[0]
    rbac.modifier_utilisateur(conn, admin_id, role="admin")    # ne doit pas lever


# ═══════════════════════════ JOURNAL D'AUDIT : RECHERCHE ═══════════════════════════

@pytest.fixture
def audit_jeu(conn):
    # NOTE : init_schema (fixture `conn`) a déjà inscrit un premier
    # "CREATION_UTILISATEUR" pour le compte admin/admin123 par défaut — les
    # tests ci-dessous en tiennent compte (3 entrées de test + celle-là = 4).
    rbac.ajouter_audit(conn, "CONNEXION", utilisateur="Karim")
    rbac.ajouter_audit(conn, "CONNEXION_ECHEC", utilisateur="inconnu", reussite=False,
                       details="mauvais mot de passe")
    rbac.ajouter_audit(conn, "CREATION_UTILISATEUR", utilisateur="admin",
                       cible_type="utilisateur", cible_id=42, details="vend1 (Vendeur)")
    return conn


def test_ajouter_audit_utilisateur_par_defaut_systeme(conn):
    rbac.set_utilisateur_connecte(None)
    aid = rbac.ajouter_audit(conn, "CONNEXION")
    row = conn.execute("SELECT * FROM journal_audit WHERE id=?", (aid,)).fetchone()
    assert row["utilisateur"] == "Système"


def test_ajouter_audit_utilise_la_session_si_disponible(conn):
    rbac.set_utilisateur_connecte({"id": 1, "nom_complet": "Karim", "role": "admin"})
    aid = rbac.ajouter_audit(conn, "CONNEXION")
    row = conn.execute("SELECT * FROM journal_audit WHERE id=?", (aid,)).fetchone()
    assert row["utilisateur"] == "Karim"


def test_ajouter_audit_cible_id_texte_convertie(conn):
    aid = rbac.ajouter_audit(conn, "MODIFICATION_UTILISATEUR", cible_id="42")
    row = conn.execute("SELECT * FROM journal_audit WHERE id=?", (aid,)).fetchone()
    assert row["cible_id"] == 42


def test_rechercher_audit_plus_recent_dabord(audit_jeu):
    lignes = rbac.rechercher_audit(audit_jeu)
    # Les 3 dernières entrées sont celles du test, dans l'ordre inverse
    # d'ajout ; la plus ancienne (4e) est le bootstrap du compte admin.
    assert [l["action"] for l in lignes[:3]] == \
           ["CREATION_UTILISATEUR", "CONNEXION_ECHEC", "CONNEXION"]
    assert len(lignes) == 4 and lignes[-1]["action"] == "CREATION_UTILISATEUR"


def test_rechercher_audit_par_utilisateur_et_action(audit_jeu):
    assert len(rbac.rechercher_audit(audit_jeu, utilisateur="Karim")) == 1
    assert len(rbac.rechercher_audit(audit_jeu, action="CONNEXION_ECHEC")) == 1
    assert len(rbac.rechercher_audit(audit_jeu, action="CONNEXION_ECHEC",
                                     utilisateur="Karim")) == 0


def test_rechercher_audit_texte_et_echappement(audit_jeu):
    assert len(rbac.rechercher_audit(audit_jeu, texte="mauvais mot de passe")) == 1
    assert len(rbac.rechercher_audit(audit_jeu, texte="Vendeur")) == 1
    assert len(rbac.rechercher_audit(audit_jeu, texte="%")) == 0    # pas un joker
    assert len(rbac.rechercher_audit(audit_jeu, texte="introuvable")) == 0


def test_rechercher_audit_pagination(audit_jeu):
    total = len(rbac.rechercher_audit(audit_jeu, limite=None))   # 3 du test + 1 bootstrap
    assert total == 4
    page1 = rbac.rechercher_audit(audit_jeu, limite=3, offset=0)
    page2 = rbac.rechercher_audit(audit_jeu, limite=3, offset=3)
    assert len(page1) == 3 and len(page2) == 1
    assert not {l["id"] for l in page1} & {l["id"] for l in page2}


def test_rechercher_audit_periode(conn):
    mid = rbac.ajouter_audit(conn, "CONNEXION", utilisateur="Karim")
    conn.executescript("DROP TRIGGER trg_audit_no_update;")
    conn.execute("UPDATE journal_audit SET date_action='2026-01-15 10:00:00' WHERE id=?", (mid,))
    conn.executescript("""CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON journal_audit
        BEGIN SELECT RAISE(ABORT, "Journal d'audit en lecture seule"); END;""")
    # Filtré par utilisateur pour ignorer l'entrée de bootstrap du compte admin
    assert len(rbac.rechercher_audit(conn, date_debut="2026-01-15", date_fin="2026-01-15",
                                     utilisateur="Karim")) == 1
    assert len(rbac.rechercher_audit(conn, date_debut="2026-01-16", utilisateur="Karim")) == 0
    assert len(rbac.rechercher_audit(conn, date_fin="2026-01-14", utilisateur="Karim")) == 0


# ═══════════════════════════ MOT DE PASSE : BCRYPT RÉEL ═══════════════════════════

def test_hash_password_reutilise_bcrypt_de_api_security():
    from api.security import hash_password, verify_password
    h = hash_password("un mot de passe")
    assert h != "un mot de passe"
    assert verify_password("un mot de passe", h)
    assert not verify_password("autre chose", h)


def test_deux_hash_du_meme_mdp_sont_differents(conn):
    """bcrypt sale chaque hash : deux comptes avec le même mot de passe ne
    doivent PAS avoir le même password_hash en base."""
    rbac.creer_utilisateur(conn, "u1", "Nom Un", "motdepasse", "vendeur")
    rbac.creer_utilisateur(conn, "u2", "Nom Deux", "motdepasse", "vendeur")
    h1 = conn.execute("SELECT password_hash FROM utilisateurs WHERE username='u1'").fetchone()[0]
    h2 = conn.execute("SELECT password_hash FROM utilisateurs WHERE username='u2'").fetchone()[0]
    assert h1 != h2
