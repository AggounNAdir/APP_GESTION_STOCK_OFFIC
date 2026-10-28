"""
UTILISATEURS, RÔLES ET JOURNAL D'AUDIT
=======================================

Gère les comptes de connexion à l'application bureau (distincts des comptes du
portail client et des vendeurs, qui ont leur propre mécanisme), un contrôle
d'accès par rôle fixe (pas de droits à la carte façon Silwane — voir la note
de conception dans l'analyse du dépôt), et un journal d'audit en ajout seul.

Principes
─────────
• Un utilisateur a UN rôle. Chaque rôle donne accès à un ensemble de
  CATÉGORIES de pages (le menu est filtré en conséquence) et à un ensemble
  d'ACTIONS sensibles (suppression définitive, ajustement de stock, annulation
  de bon, gestion des utilisateurs) qui restent bloquées même si la page est
  visible.
• Le journal d'audit (`journal_audit`) suit le même principe que le journal
  des mouvements de stock (api/stock_journal.py) : AJOUT SEUL, protégé par des
  triggers SQL. Il trace les connexions, échecs de connexion, et tout ce qui
  touche aux comptes utilisateurs.
• Aucune fonction ici ne fait de commit : l'appelant décide (cohérent avec le
  reste du code métier, voir modules/core.py).
• Aucune dépendance à Tkinter.

Limite connue : le contrôle est au niveau de la PAGE et de quelques ACTIONS
sensibles, pas de chaque bouton un par un. Un rôle « Lecture seule » voit donc
des pages qui contiennent des boutons d'écriture ; seules les actions les plus
sensibles (comptes utilisateurs, suppression définitive, ajustement de stock,
annulation de bon) sont bloquées quel que soit le rôle qui les tente.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from api.security import hash_password, verify_password

_log = logging.getLogger("api.rbac")

MOT_DE_PASSE_LONGUEUR_MIN = 6

# ═══════════════════════════ RÔLES ET CATÉGORIES ═══════════════════════════

ROLES = {
    "admin":         "Administrateur",
    "gestionnaire":  "Gestionnaire",
    "vendeur":       "Vendeur",
    "caissier":      "Caissier",
    "lecture_seule": "Lecture seule",
}

CATEGORIES = {
    "dashboard":    "Tableau de bord",
    "catalogue":    "Produits et grille des prix",
    "tiers":        "Clients, fournisseurs, prospects",
    "ventes":       "Ventes, factures, retours et commandes portail",
    "achats":       "Achats et retours fournisseur",
    "stock":        "Mouvements et ajustements de stock",
    "finances":     "Versements et situations",
    "rapports":     "Statistiques et analyses",
    "equipe":       "Vendeurs et suivi portail",
    "profils":      "Profils entreprise",
    "utilisateurs": "Utilisateurs et droits",
}

# Page du menu (clé utilisée par modules/app.py) → catégorie de droits
PAGE_CATEGORIE = {
    "dashboard":         "dashboard",
    "produits":          "catalogue",
    "grille_prix":       "catalogue",
    "mouvements_stock":  "stock",
    "clients":           "tiers",
    "fournisseurs":      "tiers",
    "prospects_vendeurs":"equipe",
    "factures":          "ventes",
    "bons_vente":        "ventes",
    "retours_vente":     "ventes",
    "cmd_portail":       "ventes",
    "bons_achat":        "achats",
    "retours_achat":     "achats",
    "vers_clients":      "finances",
    "vers_fourn":        "finances",
    "versements":        "finances",
    "situations":        "finances",
    "sit_clients":       "finances",
    "sit_fourn":         "finances",
    "statistiques":      "rapports",
    "stats_achats":      "rapports",
    "stats_ventes":      "rapports",
    "analyse_produits":  "rapports",
    "vendeurs":          "equipe",
    "portail_suivi":     "equipe",
    "profils":           "profils",
    "utilisateurs":      "utilisateurs",
    "journal_audit":     "utilisateurs",
}

# Rôle → catégories accessibles (le menu ne montre que celles-ci)
ROLE_CATEGORIES = {
    "admin":         set(CATEGORIES),
    "gestionnaire":  set(CATEGORIES) - {"utilisateurs"},
    "vendeur":       {"dashboard", "catalogue", "tiers", "ventes", "finances", "rapports"},
    "caissier":      {"dashboard", "ventes", "finances"},
    "lecture_seule": set(CATEGORIES) - {"utilisateurs"},
}

# Actions sensibles : bloquées quel que soit l'accès à la page qui les contient
ACTIONS = {
    "gerer_utilisateurs":       {"admin"},
    "supprimer_definitivement": {"admin", "gestionnaire"},
    "ajuster_stock":            {"admin", "gestionnaire"},
    "annuler_bon":              {"admin", "gestionnaire"},
}


def role_valide(role: str) -> bool:
    return role in ROLES


def libelle_role(role: str) -> str:
    return ROLES.get(role, role or "")


def libelle_categorie(cle: str) -> str:
    return CATEGORIES.get(cle, cle or "")


def categories_du_role(role: str) -> set:
    return set(ROLE_CATEGORIES.get(role, ()))


def peut_voir_page(role: Optional[str], page_key: str) -> bool:
    """Le rôle donne-t-il accès à cette page du menu ?"""
    if not role:
        return False
    if page_key == "retours":
        categories = ROLE_CATEGORIES.get(role, set())
        return "ventes" in categories or "achats" in categories
    categorie = PAGE_CATEGORIE.get(page_key)
    if categorie is None:      # page non répertoriée : ouverte par défaut
        return True
    return categorie in ROLE_CATEGORIES.get(role, set())


def peut(role: Optional[str], action_cle: str) -> bool:
    """Le rôle a-t-il le droit de faire cette action sensible ?"""
    if not role:
        return False
    return role in ACTIONS.get(action_cle, set())


# ═══════════════════════════ SESSION (utilisateur connecté) ═══════════════════════════

_utilisateur_connecte: Optional[dict] = None


def set_utilisateur_connecte(user: Optional[dict]) -> None:
    """
    Enregistre l'utilisateur connecté pour la session de l'application bureau.
    Répercute aussi le nom sur le journal des mouvements de stock (api/stock_journal)
    afin que chaque mouvement soit attribué au bon utilisateur, pas à la session
    Windows. Passer None à la déconnexion.
    """
    global _utilisateur_connecte
    _utilisateur_connecte = dict(user) if user else None
    try:
        from api.stock_journal import set_utilisateur_courant
        set_utilisateur_courant(user["nom_complet"] if user else None)
    except ImportError:
        pass


def get_utilisateur_connecte() -> Optional[dict]:
    return dict(_utilisateur_connecte) if _utilisateur_connecte else None


def role_courant() -> Optional[str]:
    return _utilisateur_connecte["role"] if _utilisateur_connecte else None


def peut_voir_page_courant(page_key: str) -> bool:
    return peut_voir_page(role_courant(), page_key)


def peut_courant(action_cle: str) -> bool:
    return peut(role_courant(), action_cle)


# ═══════════════════════════ AUTHENTIFICATION ═══════════════════════════

def authentifier(conn, username: str, password: str) -> Optional[dict]:
    """
    Vérifie identifiant + mot de passe. Retourne l'utilisateur (dict) si les
    identifiants sont bons ET le compte actif, sinon None. Ne modifie rien
    (pas de mise à jour de la dernière connexion ici : voir enregistrer_connexion).
    """
    username = (username or "").strip()
    if not username or not password:
        return None
    row = conn.execute(
        "SELECT * FROM utilisateurs WHERE username = ?", (username,)
    ).fetchone()
    if not row or not row["actif"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def enregistrer_connexion(conn, user_id) -> None:
    conn.execute(
        "UPDATE utilisateurs SET derniere_connexion = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(user_id)),
    )


# ═══════════════════════════ GESTION DES COMPTES ═══════════════════════════

def _valider_mot_de_passe(password: str) -> None:
    if not password or len(password) < MOT_DE_PASSE_LONGUEUR_MIN:
        raise ValueError(
            f"Le mot de passe doit contenir au moins {MOT_DE_PASSE_LONGUEUR_MIN} caractères."
        )


def nom_utilisateur_disponible(conn, username: str, exclure_id=None) -> bool:
    username = (username or "").strip()
    if not username:
        return False
    if exclure_id is None:
        row = conn.execute(
            "SELECT 1 FROM utilisateurs WHERE username = ?", (username,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM utilisateurs WHERE username = ? AND id != ?",
            (username, int(exclure_id)),
        ).fetchone()
    return row is None


def lister_utilisateurs(conn, inclure_inactifs: bool = True) -> list:
    sql = "SELECT * FROM utilisateurs"
    if not inclure_inactifs:
        sql += " WHERE actif = 1"
    sql += " ORDER BY nom_complet"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def creer_utilisateur(conn, username: str, nom_complet: str, password: str, role: str,
                      *, cree_par: Optional[str] = None, doit_changer_mdp: bool = True) -> int:
    """Crée un compte. Lève ValueError si les données sont invalides. Ne fait pas de commit."""
    username = (username or "").strip()
    nom_complet = (nom_complet or "").strip()
    if not username:
        raise ValueError("Le nom d'utilisateur est obligatoire.")
    if not nom_complet:
        raise ValueError("Le nom complet est obligatoire.")
    if not role_valide(role):
        raise ValueError(f"Rôle inconnu : {role!r}")
    _valider_mot_de_passe(password)
    if not nom_utilisateur_disponible(conn, username):
        raise ValueError(f"Le nom d'utilisateur « {username} » est déjà utilisé.")

    cur = conn.execute(
        """INSERT INTO utilisateurs
           (username, nom_complet, password_hash, role, actif, doit_changer_mdp,
            date_creation, cree_par)
           VALUES (?,?,?,?,1,?,?,?)""",
        (username, nom_complet, hash_password(password), role,
         1 if doit_changer_mdp else 0,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cree_par),
    )
    user_id = cur.lastrowid
    ajouter_audit(conn, "CREATION_UTILISATEUR", utilisateur=cree_par,
                  cible_type="utilisateur", cible_id=user_id,
                  details=f"{username} ({libelle_role(role)})")
    return user_id


def _nb_autres_admins_actifs(conn, exclure_id) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM utilisateurs WHERE role='admin' AND actif=1 AND id != ?",
        (int(exclure_id),),
    ).fetchone()[0]


def modifier_utilisateur(conn, user_id, *, nom_complet: Optional[str] = None,
                         role: Optional[str] = None, modifie_par: Optional[str] = None) -> None:
    user_id = int(user_id)
    if role is not None and not role_valide(role):
        raise ValueError(f"Rôle inconnu : {role!r}")
    if role is not None and role != "admin":
        actuel = conn.execute("SELECT role, actif FROM utilisateurs WHERE id=?", (user_id,)).fetchone()
        if actuel and actuel["role"] == "admin" and actuel["actif"]                 and _nb_autres_admins_actifs(conn, user_id) == 0:
            raise ValueError(
                "Impossible : c'est le dernier compte Administrateur actif. "
                "Créez ou réactivez un autre administrateur avant de changer ce rôle.")
    champs, valeurs = [], []
    if nom_complet is not None:
        nom_complet = nom_complet.strip()
        if not nom_complet:
            raise ValueError("Le nom complet est obligatoire.")
        champs.append("nom_complet = ?")
        valeurs.append(nom_complet)
    if role is not None:
        champs.append("role = ?")
        valeurs.append(role)
    if not champs:
        return
    valeurs.append(user_id)
    conn.execute(f"UPDATE utilisateurs SET {', '.join(champs)} WHERE id = ?", valeurs)
    ajouter_audit(conn, "MODIFICATION_UTILISATEUR", utilisateur=modifie_par,
                  cible_type="utilisateur", cible_id=user_id,
                  details=f"nom_complet={nom_complet!r} role={role!r}")


def activer_utilisateur(conn, user_id, actif: bool, modifie_par: Optional[str] = None) -> None:
    user_id = int(user_id)
    if not actif:
        actuel = conn.execute("SELECT role, actif FROM utilisateurs WHERE id=?", (user_id,)).fetchone()
        if actuel and actuel["role"] == "admin" and actuel["actif"]                 and _nb_autres_admins_actifs(conn, user_id) == 0:
            raise ValueError(
                "Impossible : c'est le dernier compte Administrateur actif. "
                "Créez ou réactivez un autre administrateur avant de désactiver celui-ci.")
    conn.execute("UPDATE utilisateurs SET actif = ? WHERE id = ?", (1 if actif else 0, user_id))
    ajouter_audit(conn, "ACTIVATION_UTILISATEUR" if actif else "DESACTIVATION_UTILISATEUR",
                  utilisateur=modifie_par, cible_type="utilisateur", cible_id=user_id)


def changer_mot_de_passe(conn, user_id, nouveau_mdp: str, *,
                         doit_changer_mdp: bool = False, modifie_par: Optional[str] = None) -> None:
    _valider_mot_de_passe(nouveau_mdp)
    user_id = int(user_id)
    conn.execute(
        "UPDATE utilisateurs SET password_hash = ?, doit_changer_mdp = ? WHERE id = ?",
        (hash_password(nouveau_mdp), 1 if doit_changer_mdp else 0, user_id),
    )
    ajouter_audit(conn, "CHANGEMENT_MOT_DE_PASSE", utilisateur=modifie_par,
                  cible_type="utilisateur", cible_id=user_id)


def bootstrap_admin_par_defaut(conn) -> Optional[int]:
    """
    Si la base ne contient AUCUN utilisateur (première installation, ou mise à
    niveau depuis une version sans comptes), crée un compte administrateur par
    défaut (admin / admin123) qui devra changer son mot de passe à la première
    connexion. Sans effet si des comptes existent déjà. Ne fait pas de commit.
    """
    nb = conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
    if nb > 0:
        return None
    user_id = creer_utilisateur(
        conn, "admin", "Administrateur", "admin123", "admin",
        cree_par="Système", doit_changer_mdp=True,
    )
    _log.warning(
        "Aucun compte utilisateur trouvé : compte 'admin' créé avec le mot de "
        "passe par défaut 'admin123' — à changer immédiatement à la connexion."
    )
    return user_id


# ═══════════════════════════ JOURNAL D'AUDIT ═══════════════════════════

def ajouter_audit(conn, action: str, *, utilisateur: Optional[str] = None,
                  cible_type: Optional[str] = None, cible_id=None,
                  details: Optional[str] = None, reussite: bool = True) -> int:
    """Ajoute une ligne au journal d'audit. Ne fait pas de commit."""
    if utilisateur is None:
        session = get_utilisateur_connecte()
        utilisateur = session["nom_complet"] if session else "Système"
    if cible_id is not None:
        try:
            cible_id = int(cible_id)
        except (TypeError, ValueError):
            cible_id = None
    cur = conn.execute(
        """INSERT INTO journal_audit
           (date_action, utilisateur, action, cible_type, cible_id, details, reussite)
           VALUES (?,?,?,?,?,?,?)""",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), utilisateur, action,
         cible_type, cible_id, details, 1 if reussite else 0),
    )
    return cur.lastrowid


def _echapper_like(texte: str) -> str:
    return texte.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def rechercher_audit(conn, *, date_debut=None, date_fin=None, utilisateur=None,
                     action=None, texte=None, limite: Optional[int] = 300, offset: int = 0) -> list:
    where, params = [], []
    if date_debut:
        where.append("date_action >= ?")
        params.append(f"{date_debut} 00:00:00")
    if date_fin:
        fin = datetime.strptime(date_fin, "%Y-%m-%d") + timedelta(days=1)
        where.append("date_action < ?")
        params.append(fin.strftime("%Y-%m-%d 00:00:00"))
    if utilisateur:
        where.append("utilisateur = ?")
        params.append(utilisateur)
    if action:
        where.append("action = ?")
        params.append(action)
    texte = (texte or "").strip()
    if texte:
        motif = f"%{_echapper_like(texte)}%"
        where.append("(details LIKE ? ESCAPE '\\' OR utilisateur LIKE ? ESCAPE '\\')")
        params.extend([motif, motif])
    sql = "SELECT * FROM journal_audit"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        params = params + [int(limite), int(offset)]
    cur = conn.execute(sql, params)
    colonnes = [d[0] for d in cur.description]
    return [dict(zip(colonnes, ligne)) for ligne in cur.fetchall()]
