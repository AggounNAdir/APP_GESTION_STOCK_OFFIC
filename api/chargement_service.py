"""Opérations métier pour les chargements et retours de stock camion."""
import math
import sqlite3
from datetime import date
from typing import Iterable

from api.stock_journal import enregistrer_mouvement


def creer_bon_chargement(
    conn: sqlite3.Connection,
    vendeur_id: int,
    lignes: Iterable[tuple[int, float]],
    observations: str = "",
) -> dict:
    quantites: dict[int, float] = {}
    for produit_id, quantite in lignes:
        quantite = float(quantite)
        if not math.isfinite(quantite) or quantite <= 0:
            raise ValueError("Chaque quantité chargée doit être supérieure à zéro.")
        quantites[produit_id] = quantites.get(produit_id, 0.0) + quantite

    if not quantites:
        raise ValueError("Le bon doit contenir au moins un produit.")

    date_bon = date.today().isoformat()
    date_numero = date.today().strftime("%Y%m%d")
    total_colis = sum(quantites.values())
    total_pieces = 0.0

    with conn:
        vendeur = conn.execute(
            "SELECT id, nom FROM vendeurs WHERE id=? AND actif=1", (vendeur_id,)
        ).fetchone()
        if vendeur is None:
            raise ValueError("Le vendeur sélectionné n'existe pas ou est désactivé.")

        produits = {}
        for produit_id, quantite_colis in quantites.items():
            produit = conn.execute(
                """SELECT id, designation, stock_actuel,
                          COALESCE(facteur_conversion, 1) AS facteur_conversion
                   FROM produits WHERE id=? AND actif=1""",
                (produit_id,),
            ).fetchone()
            if produit is None:
                raise ValueError(f"Le produit #{produit_id} n'existe pas ou est désactivé.")

            facteur = float(produit["facteur_conversion"] or 1)
            if not math.isfinite(facteur) or facteur <= 0:
                facteur = 1.0
            pieces = quantite_colis * facteur
            stock = float(produit["stock_actuel"] or 0)
            if pieces > stock:
                raise ValueError(
                    f"Stock insuffisant pour {produit['designation']} : "
                    f"{stock:g} pièce(s) disponible(s), {pieces:g} demandée(s)."
                )
            produits[produit_id] = (produit, pieces)

        sequence = conn.execute(
            "SELECT COUNT(*) FROM bons_chargement WHERE date_chargement=?",
            (date_bon,),
        ).fetchone()[0] + 1
        numero = f"CHG-{date_numero}-{sequence:04d}"
        while conn.execute(
            "SELECT 1 FROM bons_chargement WHERE numero=?", (numero,)
        ).fetchone():
            sequence += 1
            numero = f"CHG-{date_numero}-{sequence:04d}"

        cur = conn.execute(
            """INSERT INTO bons_chargement
               (numero, date_chargement, vendeur_id, statut, total_colis, total_pieces, observations)
               VALUES (?, ?, ?, 'Validé', ?, 0, ?)""",
            (numero, date_bon, vendeur_id, total_colis, observations.strip() or None),
        )
        bon_id = cur.lastrowid

        for produit_id, quantite_colis in quantites.items():
            produit, pieces = produits[produit_id]
            stock_avant = float(produit["stock_actuel"] or 0)
            stock_apres = stock_avant - pieces
            conn.execute(
                "INSERT INTO lignes_chargement (chargement_id, produit_id, quantite_colis, quantite_pieces) VALUES (?, ?, ?, ?)",
                (bon_id, produit_id, quantite_colis, pieces),
            )
            conn.execute(
                "UPDATE produits SET stock_actuel=? WHERE id=?",
                (stock_apres, produit_id),
            )
            conn.execute(
                """INSERT INTO stock_camion_vendeur
                   (vendeur_id, produit_id, quantite_colis, quantite_pieces, date_maj)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(vendeur_id, produit_id) DO UPDATE SET
                       quantite_colis=quantite_colis + excluded.quantite_colis,
                       quantite_pieces=quantite_pieces + excluded.quantite_pieces,
                       date_maj=datetime('now')""",
                (vendeur_id, produit_id, quantite_colis, pieces),
            )
            enregistrer_mouvement(
                conn,
                produit_id,
                "CHARGEMENT_CAMION",
                stock_avant,
                stock_apres,
                quantite=-pieces,
                document_type="bon_chargement",
                document_id=bon_id,
                document_numero=numero,
                tiers_nom=vendeur["nom"],
                motif=f"Chargement camion {vendeur['nom']} ({quantite_colis:g} colis)",
                utilisateur=vendeur["nom"],
            )
            total_pieces += pieces

        conn.execute(
            "UPDATE bons_chargement SET total_pieces=? WHERE id=?",
            (total_pieces, bon_id),
        )

    return {
        "id": bon_id,
        "numero": numero,
        "total_colis": total_colis,
        "total_pieces": total_pieces,
    }


def decharger_camion(conn: sqlite3.Connection, vendeur_id: int) -> dict:
    with conn:
        vendeur = conn.execute(
            "SELECT id, nom FROM vendeurs WHERE id=? AND actif=1", (vendeur_id,)
        ).fetchone()
        if vendeur is None:
            raise ValueError("Le vendeur sélectionné n'existe pas ou est désactivé.")

        lignes = conn.execute(
            """SELECT sc.produit_id, sc.quantite_colis, sc.quantite_pieces,
                      p.designation, p.stock_actuel
               FROM stock_camion_vendeur sc
               JOIN produits p ON p.id=sc.produit_id
               WHERE sc.vendeur_id=? AND (sc.quantite_colis > 0 OR sc.quantite_pieces > 0)""",
            (vendeur_id,),
        ).fetchall()
        if not lignes:
            return {"produits": 0, "total_colis": 0.0, "total_pieces": 0.0}

        total_colis = 0.0
        total_pieces = 0.0
        for ligne in lignes:
            pieces = float(ligne["quantite_pieces"] or 0)
            colis = float(ligne["quantite_colis"] or 0)
            stock_avant = float(ligne["stock_actuel"] or 0)
            stock_apres = stock_avant + pieces
            conn.execute(
                "UPDATE produits SET stock_actuel=? WHERE id=?",
                (stock_apres, ligne["produit_id"]),
            )
            conn.execute(
                """UPDATE stock_camion_vendeur
                   SET quantite_colis=0, quantite_pieces=0, date_maj=datetime('now')
                   WHERE vendeur_id=? AND produit_id=?""",
                (vendeur_id, ligne["produit_id"]),
            )
            enregistrer_mouvement(
                conn,
                ligne["produit_id"],
                "RETOUR_CAMION",
                stock_avant,
                stock_apres,
                quantite=pieces,
                motif=f"Déchargement fin de tournée {vendeur['nom']} ({colis:g} colis)",
                utilisateur=vendeur["nom"],
            )
            total_colis += colis
            total_pieces += pieces

    return {
        "produits": len(lignes),
        "total_colis": total_colis,
        "total_pieces": total_pieces,
    }
