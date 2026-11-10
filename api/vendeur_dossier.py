"""
Dossier complet d'un vendeur (back-office).

Regroupe en UN seul endroit toutes les requêtes qui concernent un vendeur :
bons de chargement, stock du camion, ventes, versements (clients + prospects),
prospects, commandes, pointages de tournée et situation synthétique.

⚠️ Aucun import Tkinter ici : ces fonctions sont utilisées par la fenêtre
« Vendeurs » (modules/vendeurfiche.py) ET testables seules (tests/).

Règles de calcul importantes
────────────────────────────
• Une vente terrain (api/routers/tournee.py) crée un bon de vente avec
  `montant_verse` ET un versement du même montant (versements_clients ou
  versements_prospects). L'ENCAISSEMENT d'un vendeur = somme de ses
  versements ; on n'ajoute JAMAIS `bons_vente.montant_verse` en plus
  (sinon double comptage).
• Les bons « Annulé » sont exclus de tous les totaux de ventes.
• Les périodes sont des dates ISO « AAAA-MM-JJ » (bornes incluses) ;
  `None` = pas de borne.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

STATUT_ANNULE = "Annulé"


# ───────────────────────────── utilitaires ─────────────────────────────

def _periode(colonne: str, date_debut: Optional[str], date_fin: Optional[str]):
    """Clause SQL + paramètres pour filtrer `colonne` (texte ISO, avec ou sans heure)."""
    clause, params = "", []
    if date_debut:
        clause += f" AND substr({colonne}, 1, 10) >= ?"
        params.append(date_debut)
    if date_fin:
        clause += f" AND substr({colonne}, 1, 10) <= ?"
        params.append(date_fin)
    return clause, params


def _f(valeur) -> float:
    try:
        return float(valeur or 0)
    except (TypeError, ValueError):
        return 0.0


def _rows(cursor) -> list:
    return [dict(r) for r in cursor.fetchall()]


# ───────────────────────────── fiche & situation ─────────────────────────────

def get_vendeur(conn: sqlite3.Connection, vendeur_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, code, nom, tel, actif, password_hash FROM vendeurs WHERE id=?",
        (vendeur_id,),
    ).fetchone()
    return dict(row) if row else None


def situation_vendeur(conn: sqlite3.Connection, vendeur_id: int,
                      date_debut: Optional[str] = None,
                      date_fin: Optional[str] = None) -> dict:
    """Situation synthétique du vendeur sur la période (tout l'historique si vide)."""
    # Ventes (hors annulées)
    p, pp = _periode("date_bon", date_debut, date_fin)
    v = conn.execute(
        f"""SELECT COUNT(*) AS nb, COALESCE(SUM(total), 0) AS ca,
                   COALESCE(SUM(reste_payer), 0) AS credit
            FROM bons_vente
            WHERE vendeur_id=? AND COALESCE(statut, '') <> ?{p}""",
        (vendeur_id, STATUT_ANNULE, *pp),
    ).fetchone()

    # Versements encaissés (clients + prospects)
    pc, ppc = _periode("date_vers", date_debut, date_fin)
    enc = {"total": 0.0, "especes": 0.0, "nb": 0}
    for table in ("versements_clients", "versements_prospects"):
        r = conn.execute(
            f"""SELECT COUNT(*) AS nb, COALESCE(SUM(montant), 0) AS total,
                       COALESCE(SUM(CASE WHEN mode='Espèces' THEN montant ELSE 0 END), 0) AS especes
                FROM {table} WHERE vendeur_id=?{pc}""",
            (vendeur_id, *ppc),
        ).fetchone()
        enc["nb"] += r["nb"]
        enc["total"] += _f(r["total"])
        enc["especes"] += _f(r["especes"])

    # Chargements
    pch, ppch = _periode("date_chargement", date_debut, date_fin)
    ch = conn.execute(
        f"""SELECT COUNT(*) AS nb, COALESCE(SUM(total_colis), 0) AS colis
            FROM bons_chargement
            WHERE vendeur_id=? AND COALESCE(statut, '') <> ?{pch}""",
        (vendeur_id, STATUT_ANNULE, *ppch),
    ).fetchone()

    # Prospects créés
    ppr, pppr = _periode("date_creation", date_debut, date_fin)
    pr = conn.execute(
        f"""SELECT COUNT(*) AS nb,
                   COALESCE(SUM(CASE WHEN statut='Converti' THEN 1 ELSE 0 END), 0) AS convertis
            FROM prospects_clients WHERE vendeur_id=?{ppr}""",
        (vendeur_id, *pppr),
    ).fetchone()

    # Commandes en attente (toutes périodes : c'est un travail à traiter)
    attente = 0
    for table in ("commandes_clients", "commandes_prospects"):
        attente += conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE vendeur_id=? AND statut='En attente'",
            (vendeur_id,),
        ).fetchone()[0]

    # Pointages
    ppt, pppt = _periode("date_pointage", date_debut, date_fin)
    nb_pointages = conn.execute(
        f"SELECT COUNT(*) FROM tournee_pointages WHERE vendeur_id=?{ppt}",
        (vendeur_id, *pppt),
    ).fetchone()[0]

    # Camion (état actuel, indépendant de la période)
    camion = conn.execute(
        """SELECT COUNT(*) AS nb_produits,
                  COALESCE(SUM(sc.quantite_colis), 0) AS colis,
                  COALESCE(SUM(sc.quantite_pieces * COALESCE(p.prix_vente, 0)), 0) AS valeur
           FROM stock_camion_vendeur sc JOIN produits p ON p.id = sc.produit_id
           WHERE sc.vendeur_id=? AND (sc.quantite_colis > 0 OR sc.quantite_pieces > 0)""",
        (vendeur_id,),
    ).fetchone()

    return {
        "nb_ventes": v["nb"],
        "ca": _f(v["ca"]),
        "credit_accorde": _f(v["credit"]),
        "nb_versements": enc["nb"],
        "encaisse_total": enc["total"],
        "encaisse_especes": enc["especes"],
        "nb_chargements": ch["nb"],
        "colis_charges": _f(ch["colis"]),
        "nb_prospects": pr["nb"],
        "prospects_convertis": int(pr["convertis"] or 0),
        "commandes_en_attente": attente,
        "nb_pointages": nb_pointages,
        "camion_nb_produits": camion["nb_produits"],
        "camion_colis": _f(camion["colis"]),
        "camion_valeur": _f(camion["valeur"]),
    }


# ───────────────────────────── chargements & camion ─────────────────────────────

def chargements_vendeur(conn, vendeur_id, date_debut=None, date_fin=None) -> list:
    p, pp = _periode("date_chargement", date_debut, date_fin)
    return _rows(conn.execute(
        f"""SELECT id, numero, date_chargement, statut, total_colis, total_pieces, observations
            FROM bons_chargement WHERE vendeur_id=?{p} ORDER BY id DESC""",
        (vendeur_id, *pp),
    ))


def lignes_chargement(conn, bon_id: int) -> list:
    return _rows(conn.execute(
        """SELECT p.code, p.designation, p.unite, lc.quantite_colis, lc.quantite_pieces
           FROM lignes_chargement lc JOIN produits p ON p.id = lc.produit_id
           WHERE lc.chargement_id=? ORDER BY p.designation""",
        (bon_id,),
    ))


def stock_camion(conn, vendeur_id: int) -> list:
    return _rows(conn.execute(
        """SELECT p.code, p.designation, sc.quantite_colis, sc.quantite_pieces,
                  COALESCE(p.prix_vente, 0) AS prix_vente,
                  sc.quantite_pieces * COALESCE(p.prix_vente, 0) AS valeur,
                  sc.date_maj
           FROM stock_camion_vendeur sc JOIN produits p ON p.id = sc.produit_id
           WHERE sc.vendeur_id=? AND (sc.quantite_colis > 0 OR sc.quantite_pieces > 0)
           ORDER BY p.designation""",
        (vendeur_id,),
    ))


# ───────────────────────────── ventes & versements ─────────────────────────────

def ventes_vendeur(conn, vendeur_id, date_debut=None, date_fin=None) -> list:
    p, pp = _periode("b.date_bon", date_debut, date_fin)
    return _rows(conn.execute(
        f"""SELECT b.id, b.numero, b.date_bon, COALESCE(p.nom, c.nom) AS client, b.total,
                   COALESCE(b.montant_verse, 0) AS montant_verse,
                   COALESCE(b.reste_payer, 0) AS reste_payer, b.statut
            FROM bons_vente b
            LEFT JOIN clients c ON c.id = b.client_id
            LEFT JOIN prospects_clients p ON p.id = b.prospect_id
            WHERE b.vendeur_id=?{p} ORDER BY b.id DESC""",
        (vendeur_id, *pp),
    ))


def versements_vendeur(conn, vendeur_id, date_debut=None, date_fin=None) -> list:
    """Versements clients + prospects encaissés par le vendeur (plus récents d'abord)."""
    p, pp = _periode("v.date_vers", date_debut, date_fin)
    clients = _rows(conn.execute(
        f"""SELECT v.id, v.numero, v.date_vers, 'Client' AS type, c.nom AS tiers,
                   v.montant, v.mode, v.reference
            FROM versements_clients v LEFT JOIN clients c ON c.id = v.client_id
            WHERE v.vendeur_id=?{p}""",
        (vendeur_id, *pp),
    ))
    prospects = _rows(conn.execute(
        f"""SELECT v.id, v.numero, v.date_vers, 'Prospect' AS type, c.nom AS tiers,
                   v.montant, v.mode, v.reference
            FROM versements_prospects v LEFT JOIN prospects_clients c ON c.id = v.prospect_id
            WHERE v.vendeur_id=?{p}""",
        (vendeur_id, *pp),
    ))
    return sorted(clients + prospects,
                  key=lambda r: (str(r["date_vers"]), r["numero"]), reverse=True)


# ───────────────────────────── prospects, commandes, tournée ─────────────────────────────

def prospects_vendeur(conn, vendeur_id) -> list:
    return _rows(conn.execute(
        """SELECT id, code, nom, tel, adresse, wilaya, statut, date_creation,
                  COALESCE(solde, 0) AS solde, client_id
           FROM prospects_clients WHERE vendeur_id=? ORDER BY id DESC""",
        (vendeur_id,),
    ))


def commandes_vendeur(conn, vendeur_id, date_debut=None, date_fin=None) -> list:
    pc, ppc = _periode("cc.date_commande", date_debut, date_fin)
    pp_, ppp = _periode("cp.date_commande", date_debut, date_fin)
    clients = _rows(conn.execute(
        f"""SELECT cc.id, cc.numero, cc.date_commande, 'Client' AS type, c.nom AS tiers,
                   cc.statut, COALESCE(cc.total_estime, 0) AS montant
            FROM commandes_clients cc LEFT JOIN clients c ON c.id = cc.client_id
            WHERE cc.vendeur_id=?{pc}""",
        (vendeur_id, *ppc),
    ))
    prospects = _rows(conn.execute(
        f"""SELECT cp.id, cp.numero, cp.date_commande, 'Prospect' AS type, c.nom AS tiers,
                   cp.statut, COALESCE(cp.montant_total, 0) AS montant
            FROM commandes_prospects cp LEFT JOIN prospects_clients c ON c.id = cp.prospect_id
            WHERE cp.vendeur_id=?{pp_}""",
        (vendeur_id, *ppp),
    ))
    return sorted(clients + prospects,
                  key=lambda r: (str(r["date_commande"]), r["numero"]), reverse=True)


def pointages_vendeur(conn, vendeur_id, date_debut=None, date_fin=None) -> list:
    p, pp = _periode("date_pointage", date_debut, date_fin)
    return _rows(conn.execute(
        f"""SELECT id, date_pointage, code_client, nom_client, latitude, longitude, observations
            FROM tournee_pointages WHERE vendeur_id=?{p} ORDER BY id DESC""",
        (vendeur_id, *pp),
    ))


# ───────────────────────────── actions ─────────────────────────────

def convertir_prospect_en_client(conn: sqlite3.Connection, prospect_id: int) -> dict:
    """Convertit un prospect en client officiel (même règle que ProspectsPage).

    Lève ValueError si le prospect n'existe pas ou est déjà converti.
    Retourne {"client_id", "code"}.
    """
    p = conn.execute("SELECT * FROM prospects_clients WHERE id=?", (prospect_id,)).fetchone()
    if p is None:
        raise ValueError("Prospect introuvable.")
    if p["statut"] == "Converti":
        raise ValueError("Ce prospect a déjà été converti en client.")
    try:
        dernier = conn.execute("SELECT MAX(id) FROM clients").fetchone()[0] or 0
        code = f"CLT-{dernier + 1:04d}"
        cur = conn.execute(
            """INSERT INTO clients (code, nom, tel, adresse, ville, solde)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (code, p["nom"] or "Nouveau Client", p["tel"] or "", p["adresse"] or "",
             p["wilaya"] or "Algérie", 0.0),
        )
        client_id = cur.lastrowid
        conn.execute(
            "UPDATE prospects_clients SET statut='Converti', client_id=? WHERE id=?",
            (client_id, prospect_id),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    return {"client_id": client_id, "code": code}
