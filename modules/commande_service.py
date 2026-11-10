"""
Traitement par l'administration des commandes envoyées par les vendeurs
(commandes_clients et commandes_prospects) : détail, validation, validation
ajustée au stock réel, refus.

Logique métier pure (aucun Tkinter) : elle reçoit une connexion SQLite et
gère elle-même la transaction (commit / rollback). Elle reprend les règles de
CommandesClientsPage.valider_commande, avec ces garde-fous en plus :

  • seule une commande « En attente » peut être validée ou refusée
    (évite de créer deux bons de vente pour la même commande) ;
  • le bon de vente créé porte le `vendeur_id` de la commande : la vente
    apparaît dans le dossier et le chiffre d'affaires du vendeur ;
  • la validation « totale » est refusée si le stock du dépôt est insuffisant
    (au lieu de passer en stock négatif) ; la validation « ajustée » sert
    alors à ne livrer que le disponible ;
  • validation du client/prospect, bon, stock, solde et statut dans UNE
    transaction : tout passe ou rien ne change.

Convention de quantités (identique à la validation existante) : la commande
est exprimée en COLIS, le prix est par PIÈCE, le stock est en PIÈCES.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from modules.core import recalculer_cout_stock_apres_sortie

TYPE_CLIENT = "Client"
TYPE_PROSPECT = "Prospect"
STATUT_ATTENTE = "En attente"
STATUT_VALIDEE = "Validée"
STATUT_REFUSEE = "Rejetée"


class ConversionProspectRequise(ValueError):
    """Le prospect n'est pas encore client : il faut le convertir pour facturer."""


# ───────────────────────────── accès aux tables ─────────────────────────────

def _cfg(type_: str) -> dict:
    if type_ == TYPE_CLIENT:
        return {"table": "commandes_clients", "lignes": "lignes_commande_client",
                "prix": ("prix_unitaire_estime", "prix_unitaire"),
                "total": ("total_estime", "total"),
                "montant": ("total_estime", "montant_total")}
    if type_ == TYPE_PROSPECT:
        return {"table": "commandes_prospects", "lignes": "lignes_commande_prospect",
                "prix": ("prix_unitaire", "prix_unitaire_estime"),
                "total": ("total", "total_estime"),
                "montant": ("montant_total", "total_estime")}
    raise ValueError(f"Type de commande inconnu : {type_!r}")


def _col(conn, table: str, candidats) -> str:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for c in candidats:
        if c in cols:
            return c
    raise ValueError(f"Colonne introuvable dans {table} : {candidats}")


def get_commande(conn, type_: str, cmd_id: int) -> Optional[dict]:
    cfg = _cfg(type_)
    row = conn.execute(f"SELECT * FROM {cfg['table']} WHERE id=?", (cmd_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["type"] = type_
    d["montant"] = float(d.get(_col(conn, cfg["table"], cfg["montant"])) or 0)
    return d


def lignes_commande(conn, type_: str, cmd_id: int) -> list:
    """Lignes de la commande avec facteur de colisage et stock dépôt actuel."""
    cfg = _cfg(type_)
    prix = _col(conn, cfg["lignes"], cfg["prix"])
    total = _col(conn, cfg["lignes"], cfg["total"])
    rows = conn.execute(
        f"""SELECT l.produit_id, p.code, p.designation, p.unite, l.quantite,
                   l.{prix} AS prix_unitaire, l.{total} AS total,
                   COALESCE(p.facteur_conversion, 1) AS facteur,
                   COALESCE(p.stock_actuel, 0) AS stock_pieces
            FROM {cfg['lignes']} l LEFT JOIN produits p ON p.id = l.produit_id
            WHERE l.commande_id=? ORDER BY l.id""",
        (cmd_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        f = float(d["facteur"] or 1)
        d["facteur"] = f if f > 0 else 1.0
        out.append(d)
    return out


# ───────────────────────────── refus ─────────────────────────────

def rejeter_commande(conn: sqlite3.Connection, type_: str, cmd_id: int, motif: str = "") -> None:
    cfg = _cfg(type_)
    cmd = get_commande(conn, type_, cmd_id)
    if cmd is None:
        raise ValueError("Commande introuvable.")
    if cmd["statut"] != STATUT_ATTENTE:
        raise ValueError(f"Cette commande est déjà « {cmd['statut']} ».")
    obs = (cmd.get("observations") or "").strip()
    motif = (motif or "").strip()
    if motif:
        obs = (obs + f"\n[Rejet] {motif}").strip()
    conn.execute(
        f"UPDATE {cfg['table']} SET statut=?, observations=? WHERE id=?",
        (STATUT_REFUSEE, obs, cmd_id),
    )
    conn.commit()


# ───────────────────────────── validation ─────────────────────────────

def _numero_bv(conn, client_id: int) -> str:
    """BV-<client sur 5 chiffres>-<n sur 4> : même format que next_numero_tiers."""
    max_n = 0
    for (num,) in conn.execute(
            "SELECT numero FROM bons_vente WHERE client_id=? AND numero LIKE 'BV-%'",
            (client_id,)).fetchall():
        try:
            max_n = max(max_n, int(str(num).split("-")[-1]))
        except ValueError:
            continue
    return f"BV-{client_id:05d}-{max_n + 1:04d}"


def _convertir_prospect(conn, prospect) -> int:
    """Crée le client officiel du prospect (mêmes champs que ProspectsPage)."""
    dernier = conn.execute("SELECT MAX(id) FROM clients").fetchone()[0] or 0
    code = f"CLT-{dernier + 1:04d}"
    cur = conn.execute(
        """INSERT INTO clients (code, nom, tel, adresse, ville, solde)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (code, prospect["nom"] or "Nouveau Client", prospect["tel"] or "",
         prospect["adresse"] or "", prospect["wilaya"] or "Algérie"),
    )
    client_id = cur.lastrowid
    conn.execute(
        "UPDATE prospects_clients SET statut='Converti', client_id=? WHERE id=?",
        (client_id, prospect["id"]),
    )
    return client_id


def valider_commande(conn: sqlite3.Connection, type_: str, cmd_id: int, *,
                     complete: bool = True, convertir_prospect: bool = False) -> dict:
    """Valide une commande : crée le bon de vente, déstocke, met à jour le solde.

    complete=True  : toutes les quantités ; refusé si le stock du dépôt ne suffit pas.
    complete=False : valide « ajusté » : limite chaque ligne au stock réel.
    convertir_prospect : autorise la création du client officiel d'un prospect
        (sinon ConversionProspectRequise est levée pour demander confirmation).

    Retourne {"bon_id", "numero", "total", "client_id", "ajuste", "lignes"}.
    Lève ValueError (message affichable) ; rien n'est modifié en cas d'erreur.
    """
    cfg = _cfg(type_)
    cmd = get_commande(conn, type_, cmd_id)
    if cmd is None:
        raise ValueError("Commande introuvable.")
    if cmd["statut"] != STATUT_ATTENTE:
        raise ValueError(f"Cette commande est déjà « {cmd['statut']} ».")

    lignes = lignes_commande(conn, type_, cmd_id)
    if not lignes:
        raise ValueError("Cette commande n'a aucune ligne.")

    try:
        # 1) Client à facturer
        if type_ == TYPE_CLIENT:
            client_id = cmd["client_id"]
        else:
            prospect = conn.execute(
                "SELECT * FROM prospects_clients WHERE id=?", (cmd["prospect_id"],)).fetchone()
            if prospect is None:
                raise ValueError("Prospect introuvable.")
            client_id = prospect["client_id"]
            if not client_id:
                if not convertir_prospect:
                    raise ConversionProspectRequise(
                        f"Le prospect « {prospect['nom']} » n'est pas encore client officiel.")
                client_id = _convertir_prospect(conn, prospect)

        # 2) Quantités servies (cumul par produit : un produit peut être sur 2 lignes)
        reste_stock = {}
        servies, manques = [], []
        for l in lignes:
            pid = l["produit_id"]
            if pid not in reste_stock:
                reste_stock[pid] = float(l["stock_pieces"] or 0)
            facteur = l["facteur"]
            demande_colis = float(l["quantite"] or 0)
            dispo_colis = max(0.0, reste_stock[pid] / facteur)
            if complete:
                if demande_colis > dispo_colis + 1e-9:
                    manques.append(
                        f"{l['designation']} (demandé {demande_colis:g} colis, "
                        f"disponible {dispo_colis:g})")
                    continue
                colis = demande_colis
            else:
                colis = min(demande_colis, dispo_colis)
            if colis <= 0:
                continue
            pieces = colis * facteur
            reste_stock[pid] -= pieces
            prix = float(l["prix_unitaire"] or 0)
            servies.append({
                "produit_id": pid, "colis": colis, "pieces": pieces, "prix": prix,
                "total": round(pieces * prix, 2),
                "reduit": colis + 1e-9 < demande_colis,
            })
        if manques:
            raise ValueError(
                "Stock insuffisant pour :\n• " + "\n• ".join(manques) +
                "\n\nUtilisez « Valider ajusté » pour ne livrer que le stock disponible.")
        if not servies:
            raise ValueError("Aucun article disponible en stock pour cette commande.")

        total = round(sum(s["total"] for s in servies), 2)
        ajuste = any(s["reduit"] for s in servies) or len(servies) < len(lignes)

        # 3) Bon de vente (rattaché au vendeur de la commande) + lignes + stock
        today = date.today().isoformat()
        numero = _numero_bv(conn, client_id)
        cur = conn.execute(
            """INSERT INTO bons_vente
                   (numero, date_bon, client_id, vendeur_id, total, montant_verse,
                    reste_payer, statut, observations)
               VALUES (?, ?, ?, ?, ?, 0, ?, 'Validé', ?)""",
            (numero, today, client_id, cmd.get("vendeur_id"), total, total,
             f"Commande {cmd['numero']}"),
        )
        bon_id = cur.lastrowid
        for s in servies:
            conn.execute(
                """INSERT INTO lignes_vente (bon_id, produit_id, quantite, prix_unitaire, total)
                   VALUES (?, ?, ?, ?, ?)""",
                (bon_id, s["produit_id"], s["pieces"], s["prix"], s["total"]))
            recalculer_cout_stock_apres_sortie(
                conn, s["produit_id"], s["pieces"],
                type_mouvement="VENTE", document_type="bon_vente", document_id=bon_id,
                document_numero=numero, date_document=today,
                motif=f"Validation de la commande {cmd['numero']}")

        # 4) Solde du client (sauf COMPTOIR)
        conn.execute(
            "UPDATE clients SET solde = COALESCE(solde, 0) + ? WHERE id=? AND nom <> 'COMPTOIR'",
            (total, client_id))

        # 5) Statut de la commande
        obs = (cmd.get("observations") or "").strip()
        if ajuste:
            obs = (obs + "\n[Validée ajustée au stock disponible]").strip()
        if type_ == TYPE_CLIENT:
            conn.execute(
                "UPDATE commandes_clients SET statut=?, bon_vente_id=?, observations=? WHERE id=?",
                (STATUT_VALIDEE, bon_id, obs, cmd_id))
        else:
            conn.execute(
                "UPDATE commandes_prospects SET statut=?, observations=? WHERE id=?",
                (STATUT_VALIDEE, obs, cmd_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {"bon_id": bon_id, "numero": numero, "total": total, "client_id": client_id,
            "ajuste": ajuste, "lignes": len(servies)}
