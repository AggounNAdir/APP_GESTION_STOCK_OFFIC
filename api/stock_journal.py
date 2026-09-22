"""
JOURNAL DES MOUVEMENTS DE STOCK
================================

Chaque variation de `produits.stock_actuel` laisse une trace dans la table
`mouvements_stock` : quoi (produit, quantité), quand, pourquoi (type), sur
quel document (bon d'achat/vente, retour...), avec quel coût, par qui.

Principes
─────────
• Le journal est en AJOUT SEUL : des triggers SQL (voir api/schema.py) refusent
  tout UPDATE / DELETE. Une erreur se corrige par un mouvement inverse
  (ajustement ou régularisation), jamais en effaçant l'historique.
• `quantite` est SIGNÉE, en unité de base du produit (+ = entrée, − = sortie).
  On enregistre la variation RÉELLEMENT appliquée au stock (par ex. si une
  annulation d'achat est plafonnée à 0, c'est le delta réel qui est journalisé)
  afin que  SUM(quantite) == stock_actuel  reste vrai.
• Ce module ne fait AUCUN commit : le mouvement fait partie de la transaction
  de l'opération métier (vente, achat...). Si elle est annulée (rollback), le
  mouvement l'est aussi.
• Aucune dépendance à Tkinter : utilisable par l'application bureau, l'API et
  les scripts.

Points d'entrée pour le reste du code
─────────────────────────────────────
    enregistrer_mouvement(...)   écrit une ligne du journal
    rechercher_mouvements(...)   lecture filtrée / paginée
    totaliser_mouvements(...)    totaux pour les mêmes filtres
    verifier_coherence(...)      produits dont le stock ≠ somme du journal
    regulariser_ecarts(...)      réconcilie le journal avec le stock
    reprise_stock_existant(...)  ouverture du journal sur une base existante

Les opérations de stock elles-mêmes (PMP, entrées, sorties, ajustements) sont
dans modules/core.py : elles appellent `enregistrer_mouvement`.
"""
import getpass
import logging
from datetime import datetime, timedelta
from typing import Optional

_log = logging.getLogger("api.stock_journal")

# Écart toléré entre stock_actuel et la somme du journal (bruit des flottants).
TOLERANCE = 1e-4

# ═══════════════════════════ VOCABULAIRE ═══════════════════════════

# code → libellé affiché. Le SENS (entrée/sortie) se déduit du signe de la
# quantité, pas du type : un ajustement peut aller dans les deux sens.
TYPES_MOUVEMENT = {
    "STOCK_INITIAL":           "Stock initial",
    "REPRISE":                 "Reprise de stock existant",
    "ACHAT":                   "Achat",
    "RETOUR_VENTE":            "Retour client",
    "ANNULATION_VENTE":        "Annulation de vente",
    "ANNULATION_RETOUR_ACHAT": "Annulation retour fournisseur",
    "VENTE":                   "Vente",
    "RETOUR_ACHAT":            "Retour fournisseur",
    "ANNULATION_ACHAT":        "Annulation d'achat",
    "ANNULATION_RETOUR_VENTE": "Annulation retour client",
    "AJUSTEMENT":              "Ajustement manuel",
    "REGULARISATION":          "Régularisation",
}

# type de document → (libellé, table, colonne date, colonne tiers, table tiers)
_DOCUMENTS = {
    "bon_achat":    ("Bon d'achat",        "bons_achat",    "date_bon",    "fournisseur_id", "fournisseurs"),
    "bon_vente":    ("Bon de vente",       "bons_vente",    "date_bon",    "client_id",      "clients"),
    "retour_vente": ("Retour client",      "retours_vente", "date_retour", "client_id",      "clients"),
    "retour_achat": ("Retour fournisseur", "retours_achat", "date_retour", "fournisseur_id", "fournisseurs"),
}
TYPES_DOCUMENT = {code: spec[0] for code, spec in _DOCUMENTS.items()}


def libelle_type(code: str) -> str:
    return TYPES_MOUVEMENT.get(code, code or "")


def libelle_document(code: Optional[str]) -> str:
    return TYPES_DOCUMENT.get(code, code or "")


# ═══════════════════════════ UTILISATEUR ═══════════════════════════

_utilisateur_courant: Optional[str] = None


def set_utilisateur_courant(nom: Optional[str]) -> None:
    """À appeler par le futur système de connexion : le nom sera inscrit sur
    chaque mouvement. Sans appel, on utilise le nom de session du système."""
    global _utilisateur_courant
    _utilisateur_courant = (nom or "").strip() or None


def get_utilisateur_courant() -> str:
    if _utilisateur_courant:
        return _utilisateur_courant
    try:
        return getpass.getuser()
    except Exception:  # pas de nom de session (service, conteneur...)
        return "Système"


# ═══════════════════════════ ÉCRITURE ═══════════════════════════

def _resoudre_document(conn, document_type, document_id):
    """Retrouve (numéro, tiers, date) d'un document à partir de son id.
    Retourne (None, None, None) si le document est inconnu (ou supprimé)."""
    spec = _DOCUMENTS.get(document_type)
    if not spec or document_id is None:
        return None, None, None
    _, table, col_date, col_tiers, table_tiers = spec  # noms venant du dict ci-dessus
    row = conn.execute(
        f"SELECT d.numero, t.nom, d.{col_date} FROM {table} d "
        f"LEFT JOIN {table_tiers} t ON t.id = d.{col_tiers} WHERE d.id = ?",
        (document_id,),
    ).fetchone()
    if not row:
        return None, None, None
    return row[0], row[1], row[2]


def enregistrer_mouvement(
    conn,
    produit_id,
    type_mouvement: str,
    stock_avant,
    stock_apres,
    *,
    quantite=None,
    cout_unitaire=0.0,
    pmp_apres=None,
    document_type: Optional[str] = None,
    document_id=None,
    document_numero: Optional[str] = None,
    tiers_nom: Optional[str] = None,
    date_document: Optional[str] = None,
    motif: Optional[str] = None,
    utilisateur: Optional[str] = None,
) -> Optional[int]:
    """
    Ajoute un mouvement au journal. Retourne son id, ou None si la variation
    est nulle (rien n'a bougé : on n'écrit pas de ligne vide).

    `quantite` est déduite de stock_apres − stock_avant si elle n'est pas
    fournie. Si `document_type` + `document_id` sont donnés, le numéro du
    document, le tiers et sa date sont retrouvés automatiquement (ils restent
    conservés dans le journal même si le document est supprimé ensuite).
    Ne fait pas de commit.
    """
    if type_mouvement not in TYPES_MOUVEMENT:
        raise ValueError(f"Type de mouvement de stock inconnu : {type_mouvement!r}")

    stock_avant = float(stock_avant or 0)
    stock_apres = float(stock_apres or 0)
    if quantite is None:
        quantite = stock_apres - stock_avant
    quantite = round(float(quantite), 6)
    if abs(quantite) < 1e-9:
        return None

    if document_id is not None:
        try:
            document_id = int(document_id)  # les Treeview renvoient des iid texte
        except (TypeError, ValueError):
            document_id = None
    if document_type and document_id is not None and (
            document_numero is None or tiers_nom is None or date_document is None):
        num, tiers, dt = _resoudre_document(conn, document_type, document_id)
        document_numero = document_numero if document_numero is not None else num
        tiers_nom = tiers_nom if tiers_nom is not None else tiers
        date_document = date_document if date_document is not None else dt

    cout = float(cout_unitaire or 0)
    cur = conn.execute(
        """INSERT INTO mouvements_stock
           (date_mouvement, date_document, produit_id, type_mouvement, quantite,
            stock_avant, stock_apres, cout_unitaire, valeur, pmp_apres,
            document_type, document_id, document_numero, tiers_nom, motif, utilisateur)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            date_document,
            int(produit_id),
            type_mouvement,
            quantite,
            round(stock_avant, 6),
            round(stock_apres, 6),
            cout,
            round(quantite * cout, 4),
            None if pmp_apres is None else float(pmp_apres),
            document_type,
            document_id,
            document_numero,
            tiers_nom,
            (motif or "").strip() or None,
            (utilisateur or "").strip() or get_utilisateur_courant(),
        ),
    )
    return cur.lastrowid


# ═══════════════════════════ LECTURE ═══════════════════════════

def _echapper_like(texte: str) -> str:
    return texte.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _clause_filtres(date_debut, date_fin, produit_id, types, sens, texte,
                    document_type, document_id):
    """Construit (WHERE, paramètres) commun à la liste et aux totaux."""
    where, params = [], []
    if date_debut:
        where.append("m.date_mouvement >= ?")
        params.append(f"{date_debut} 00:00:00")
    if date_fin:
        # borne haute exclusive = lendemain 00:00:00 (inclut toute la journée)
        fin = datetime.strptime(date_fin, "%Y-%m-%d") + timedelta(days=1)
        where.append("m.date_mouvement < ?")
        params.append(fin.strftime("%Y-%m-%d 00:00:00"))
    if produit_id:
        where.append("m.produit_id = ?")
        params.append(int(produit_id))
    if types:
        where.append(f"m.type_mouvement IN ({','.join('?' * len(types))})")
        params.extend(types)
    if sens == "entree":
        where.append("m.quantite > 0")
    elif sens == "sortie":
        where.append("m.quantite < 0")
    if document_type:
        where.append("m.document_type = ?")
        params.append(document_type)
    if document_id is not None:
        where.append("m.document_id = ?")
        params.append(int(document_id))
    texte = (texte or "").strip()
    if texte:
        motif = f"%{_echapper_like(texte)}%"
        where.append(
            "(m.document_numero LIKE ? ESCAPE '\\' OR m.tiers_nom LIKE ? ESCAPE '\\' "
            "OR m.motif LIKE ? ESCAPE '\\' OR p.code LIKE ? ESCAPE '\\' "
            "OR p.designation LIKE ? ESCAPE '\\' OR p.barcode LIKE ? ESCAPE '\\')"
        )
        params.extend([motif] * 6)
    return (" AND ".join(where) if where else "1=1"), params


def rechercher_mouvements(
    conn, *, date_debut=None, date_fin=None, produit_id=None, types=None,
    sens=None, texte=None, document_type=None, document_id=None,
    limite: Optional[int] = 500, offset: int = 0,
) -> list:
    """
    Liste les mouvements (plus récents d'abord) sous forme de dicts, avec le
    code, la désignation, l'unité et le facteur de conversion du produit.
    Dates au format 'YYYY-MM-DD'. `sens` : 'entree' | 'sortie' | None.
    `limite=None` retourne tout (exports).
    """
    where, params = _clause_filtres(date_debut, date_fin, produit_id, types, sens,
                                    texte, document_type, document_id)
    sql = (
        "SELECT m.*, p.code AS produit_code, p.designation AS produit_designation, "
        "       p.unite AS produit_unite, p.facteur_conversion AS produit_facteur "
        "FROM mouvements_stock m JOIN produits p ON p.id = m.produit_id "
        f"WHERE {where} ORDER BY m.id DESC"
    )
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        params = params + [int(limite), int(offset)]
    cur = conn.execute(sql, params)
    colonnes = [d[0] for d in cur.description]
    return [dict(zip(colonnes, ligne)) for ligne in cur.fetchall()]


def totaliser_mouvements(
    conn, *, date_debut=None, date_fin=None, produit_id=None, types=None,
    sens=None, texte=None, document_type=None, document_id=None,
) -> dict:
    """Totaux pour les mêmes filtres que rechercher_mouvements."""
    where, params = _clause_filtres(date_debut, date_fin, produit_id, types, sens,
                                    texte, document_type, document_id)
    row = conn.execute(
        "SELECT COUNT(*), "
        "  COALESCE(SUM(CASE WHEN m.quantite > 0 THEN m.quantite END), 0), "
        "  COALESCE(SUM(CASE WHEN m.quantite < 0 THEN -m.quantite END), 0), "
        "  COALESCE(SUM(CASE WHEN m.quantite > 0 THEN m.valeur END), 0), "
        "  COALESCE(SUM(CASE WHEN m.quantite < 0 THEN -m.valeur END), 0) "
        "FROM mouvements_stock m JOIN produits p ON p.id = m.produit_id "
        f"WHERE {where}",
        params,
    ).fetchone()
    return {
        "nombre": row[0],
        "entrees": row[1],
        "sorties": row[2],
        "valeur_entrees": row[3],
        "valeur_sorties": row[4],
    }


# ═══════════════════════════ COHÉRENCE ═══════════════════════════

def stock_selon_journal(conn, produit_id) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(quantite), 0) FROM mouvements_stock WHERE produit_id = ?",
        (int(produit_id),),
    ).fetchone()
    return float(row[0])


def verifier_coherence(conn) -> list:
    """
    Produits dont `stock_actuel` ne correspond pas à la somme de leurs
    mouvements. Un écart signale une modification du stock qui n'est pas passée
    par le journal (import, script, ancienne version de l'application...).
    """
    cur = conn.execute(
        """SELECT p.id, p.code, p.designation, p.unite,
                  COALESCE(p.stock_actuel, 0) AS stock_actuel,
                  COALESCE(SUM(m.quantite), 0) AS stock_journal
           FROM produits p LEFT JOIN mouvements_stock m ON m.produit_id = p.id
           GROUP BY p.id
           HAVING ABS(COALESCE(p.stock_actuel, 0) - COALESCE(SUM(m.quantite), 0)) > ?
           ORDER BY p.designation""",
        (TOLERANCE,),
    )
    ecarts = []
    for r in cur.fetchall():
        ecarts.append({
            "produit_id": r[0], "code": r[1], "designation": r[2], "unite": r[3],
            "stock_actuel": float(r[4]), "stock_journal": float(r[5]),
            "ecart": float(r[4]) - float(r[5]),
        })
    return ecarts


def regulariser_ecarts(conn, produit_ids=None, utilisateur: Optional[str] = None) -> int:
    """
    Réconcilie le journal avec le stock : pour chaque produit en écart, ajoute
    un mouvement 'REGULARISATION' égal à l'écart. Le stock du produit n'est PAS
    modifié (on considère que `stock_actuel` fait foi) ; seul l'historique est
    complété, avec une trace explicite de la correction. Retourne le nombre de
    produits régularisés. Ne fait pas de commit.
    """
    voulus = None if produit_ids is None else {int(i) for i in produit_ids}
    nb = 0
    for e in verifier_coherence(conn):
        if voulus is not None and e["produit_id"] not in voulus:
            continue
        row = conn.execute(
            "SELECT prix_moyen_pondere, prix_achat FROM produits WHERE id=?",
            (e["produit_id"],),
        ).fetchone()
        pmp = float(row[0] or 0) if row else 0.0
        cout = pmp if pmp > 0 else (float(row[1] or 0) if row else 0.0)
        enregistrer_mouvement(
            conn, e["produit_id"], "REGULARISATION",
            stock_avant=e["stock_journal"], stock_apres=e["stock_actuel"],
            cout_unitaire=cout, pmp_apres=pmp or None,
            motif=(f"Régularisation : le stock enregistré ({e['stock_actuel']:g}) "
                   f"différait du journal ({e['stock_journal']:g})"),
            utilisateur=utilisateur,
        )
        nb += 1
    return nb


# ═══════════════════════════ OUVERTURE DU JOURNAL ═══════════════════════════

def reprise_stock_existant(conn) -> int:
    """
    Ouvre le journal sur une base qui existait avant lui : chaque produit ayant
    du stock mais AUCUN mouvement reçoit une ligne 'REPRISE' égale à son stock.
    Idempotent (un produit déjà journalisé n'est jamais retouché) et atomique :
    une seule requête, sûre même si le bureau et l'API démarrent en même temps.
    Retourne le nombre de lignes créées. Ne fait pas de commit.
    """
    cur = conn.execute(
        """INSERT INTO mouvements_stock
           (date_mouvement, produit_id, type_mouvement, quantite, stock_avant,
            stock_apres, cout_unitaire, valeur, pmp_apres, motif, utilisateur)
           SELECT ?, p.id, 'REPRISE', p.stock_actuel, 0, p.stock_actuel,
                  p.cout, ROUND(p.stock_actuel * p.cout, 4),
                  NULLIF(COALESCE(p.prix_moyen_pondere, 0), 0), ?, 'Système'
           FROM (SELECT id, stock_actuel, prix_moyen_pondere,
                        CASE WHEN COALESCE(prix_moyen_pondere, 0) > 0
                             THEN prix_moyen_pondere ELSE COALESCE(prix_achat, 0) END AS cout
                 FROM produits WHERE COALESCE(stock_actuel, 0) <> 0) p
           WHERE NOT EXISTS (SELECT 1 FROM mouvements_stock m WHERE m.produit_id = p.id)""",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Reprise du stock existant à l'ouverture du journal des mouvements",
        ),
    )
    nb = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    if nb:
        _log.info("Journal des mouvements : %d produit(s) repris avec leur stock existant", nb)
    return nb
