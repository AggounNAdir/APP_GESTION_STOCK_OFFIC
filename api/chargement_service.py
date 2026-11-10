"""Opérations métier pour les chargements et retours de stock camion."""
import math
import sqlite3
from datetime import date
from typing import Iterable

from api.stock_journal import enregistrer_mouvement, supprimer_mouvements_document


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


def modifier_bon_chargement(
    conn: sqlite3.Connection,
    bon_id: int,
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

    with conn:
        bon = conn.execute(
            """SELECT b.id, b.numero, b.vendeur_id, b.statut, v.nom AS vendeur_nom
               FROM bons_chargement b
               JOIN vendeurs v ON v.id = b.vendeur_id
               WHERE b.id=?""",
            (bon_id,),
        ).fetchone()
        if bon is None:
            raise ValueError("Le bon de chargement sélectionné n'existe pas.")
        if bon["statut"] != "Validé":
            raise ValueError("Seul un bon de chargement validé peut être modifié.")

        anciennes = {
            row["produit_id"]: {
                "colis": float(row["colis"] or 0),
                "pieces": float(row["pieces"] or 0),
            }
            for row in conn.execute(
                """SELECT produit_id, SUM(quantite_colis) AS colis,
                          SUM(quantite_pieces) AS pieces
                   FROM lignes_chargement WHERE chargement_id=?
                   GROUP BY produit_id""",
                (bon_id,),
            ).fetchall()
        }

        changements = []
        total_colis = 0.0
        total_pieces = 0.0
        for produit_id in sorted(set(anciennes) | set(quantites)):
            produit = conn.execute(
                """SELECT id, designation, stock_actuel,
                          COALESCE(facteur_conversion, 1) AS facteur_conversion,
                          actif
                   FROM produits WHERE id=?""",
                (produit_id,),
            ).fetchone()
            if produit is None:
                raise ValueError(f"Le produit #{produit_id} n'existe plus.")
            if produit_id in quantites and not produit["actif"] and produit_id not in anciennes:
                raise ValueError(f"Le produit {produit['designation']} est désactivé.")

            facteur = float(produit["facteur_conversion"] or 1)
            if not math.isfinite(facteur) or facteur <= 0:
                facteur = 1.0
            ancien = anciennes.get(produit_id, {"colis": 0.0, "pieces": 0.0})
            nouveau_colis = quantites.get(produit_id, 0.0)
            nouveau_pieces = nouveau_colis * facteur
            delta_colis = nouveau_colis - ancien["colis"]
            delta_pieces = nouveau_pieces - ancien["pieces"]
            stock_depot = float(produit["stock_actuel"] or 0)

            camion = conn.execute(
                """SELECT quantite_colis, quantite_pieces
                   FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?""",
                (bon["vendeur_id"], produit_id),
            ).fetchone()
            camion_colis = float(camion["quantite_colis"] or 0) if camion else 0.0
            camion_pieces = float(camion["quantite_pieces"] or 0) if camion else 0.0
            if delta_pieces > stock_depot + 1e-9:
                raise ValueError(
                    f"Stock dépôt insuffisant pour {produit['designation']} : "
                    f"{stock_depot:g} pièce(s) disponible(s), {delta_pieces:g} supplémentaire(s) nécessaire(s)."
                )
            if delta_colis < -camion_colis - 1e-9 or delta_pieces < -camion_pieces - 1e-9:
                raise ValueError(
                    f"Modification impossible pour {produit['designation']} : "
                    "le stock disponible dans le camion ne permet pas de retirer cette quantité."
                )

            changements.append(
                (produit_id, produit, ancien, nouveau_colis, nouveau_pieces,
                 delta_colis, delta_pieces, camion_colis, camion_pieces)
            )
            total_colis += nouveau_colis
            total_pieces += nouveau_pieces

        for (produit_id, produit, ancien, nouveau_colis, nouveau_pieces,
             delta_colis, delta_pieces, camion_colis, camion_pieces) in changements:
            stock_avant = float(produit["stock_actuel"] or 0)
            stock_apres = stock_avant - delta_pieces
            conn.execute(
                "UPDATE produits SET stock_actuel=? WHERE id=?",
                (stock_apres, produit_id),
            )
            if conn.execute(
                "SELECT 1 FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
                (bon["vendeur_id"], produit_id),
            ).fetchone():
                conn.execute(
                    """UPDATE stock_camion_vendeur
                       SET quantite_colis=MAX(0, quantite_colis+?),
                           quantite_pieces=MAX(0, quantite_pieces+?),
                           date_maj=datetime('now')
                       WHERE vendeur_id=? AND produit_id=?""",
                    (delta_colis, delta_pieces, bon["vendeur_id"], produit_id),
                )
            else:
                conn.execute(
                    """INSERT INTO stock_camion_vendeur
                       (vendeur_id, produit_id, quantite_colis, quantite_pieces, date_maj)
                       VALUES (?, ?, ?, ?, datetime('now'))""",
                    (bon["vendeur_id"], produit_id, delta_colis, delta_pieces),
                )
            if abs(delta_pieces) > 1e-9:
                enregistrer_mouvement(
                    conn,
                    produit_id,
                    "CORRECTION_CHARGEMENT",
                    stock_avant,
                    stock_apres,
                    quantite=-delta_pieces,
                    document_type="bon_chargement",
                    document_id=bon_id,
                    document_numero=bon["numero"],
                    tiers_nom=bon["vendeur_nom"],
                    motif=(
                        f"Modification du bon {bon['numero']} : "
                        f"{ancien['colis']:g} → {nouveau_colis:g} colis"
                    ),
                    utilisateur=bon["vendeur_nom"],
                )

        conn.execute("DELETE FROM lignes_chargement WHERE chargement_id=?", (bon_id,))
        for produit_id, quantite_colis in quantites.items():
            facteur_row = next(c for c in changements if c[0] == produit_id)
            nouveau_pieces = facteur_row[4]
            conn.execute(
                """INSERT INTO lignes_chargement
                   (chargement_id, produit_id, quantite_colis, quantite_pieces)
                   VALUES (?, ?, ?, ?)""",
                (bon_id, produit_id, quantite_colis, nouveau_pieces),
            )
        conn.execute(
            """UPDATE bons_chargement
               SET total_colis=?, total_pieces=?, observations=?
               WHERE id=?""",
            (total_colis, total_pieces, observations.strip() or None, bon_id),
        )

    return {
        "id": bon_id,
        "numero": bon["numero"],
        "total_colis": total_colis,
        "total_pieces": total_pieces,
    }


def annuler_bon_chargement(conn: sqlite3.Connection, bon_id: int) -> dict:
    with conn:
        bon = conn.execute(
            """SELECT b.id, b.numero, b.vendeur_id, b.statut, v.nom AS vendeur_nom
               FROM bons_chargement b
               JOIN vendeurs v ON v.id = b.vendeur_id
               WHERE b.id=?""",
            (bon_id,),
        ).fetchone()
        if bon is None:
            raise ValueError("Le bon de chargement sélectionné n'existe pas.")
        if bon["statut"] != "Validé":
            raise ValueError("Seul un bon de chargement validé peut être annulé.")

        lignes = conn.execute(
            """SELECT lc.produit_id, lc.quantite_colis, lc.quantite_pieces,
                      p.designation, p.stock_actuel,
                      COALESCE(sc.quantite_colis, 0) AS camion_colis,
                      COALESCE(sc.quantite_pieces, 0) AS camion_pieces
               FROM lignes_chargement lc
               JOIN produits p ON p.id=lc.produit_id
               LEFT JOIN stock_camion_vendeur sc
                 ON sc.vendeur_id=? AND sc.produit_id=lc.produit_id
               WHERE lc.chargement_id=?""",
            (bon["vendeur_id"], bon_id),
        ).fetchall()
        if not lignes:
            raise ValueError("Le bon ne contient aucune ligne à annuler.")

        for ligne in lignes:
            colis = float(ligne["quantite_colis"] or 0)
            pieces = float(ligne["quantite_pieces"] or 0)
            if (colis > float(ligne["camion_colis"] or 0) + 1e-9
                    or pieces > float(ligne["camion_pieces"] or 0) + 1e-9):
                raise ValueError(
                    f"Annulation impossible pour {ligne['designation']} : "
                    "le stock disponible dans le camion ne permet pas de retourner "
                    "toute la quantité du bon."
                )

        for ligne in lignes:
            colis = float(ligne["quantite_colis"] or 0)
            pieces = float(ligne["quantite_pieces"] or 0)
            stock_avant = float(ligne["stock_actuel"] or 0)
            stock_apres = stock_avant + pieces
            conn.execute(
                "UPDATE produits SET stock_actuel=? WHERE id=?",
                (stock_apres, ligne["produit_id"]),
            )
            conn.execute(
                """UPDATE stock_camion_vendeur
                   SET quantite_colis=MAX(0, quantite_colis-?),
                       quantite_pieces=MAX(0, quantite_pieces-?),
                       date_maj=datetime('now')
                   WHERE vendeur_id=? AND produit_id=?""",
                (colis, pieces, bon["vendeur_id"], ligne["produit_id"]),
            )
            enregistrer_mouvement(
                conn,
                ligne["produit_id"],
                "ANNULATION_CHARGEMENT",
                stock_avant,
                stock_apres,
                quantite=pieces,
                document_type="bon_chargement",
                document_id=bon_id,
                document_numero=bon["numero"],
                tiers_nom=bon["vendeur_nom"],
                motif=f"Annulation du bon {bon['numero']} : retour de {colis:g} colis",
                utilisateur=bon["vendeur_nom"],
            )

        conn.execute(
            "UPDATE bons_chargement SET statut='Annulé' WHERE id=?",
            (bon_id,),
        )

    return {"id": bon_id, "numero": bon["numero"], "statut": "Annulé"}


def supprimer_bon_chargement(conn: sqlite3.Connection, bon_id: int) -> dict:
    with conn:
        bon = conn.execute(
            """SELECT b.id, b.numero, b.vendeur_id, b.statut
               FROM bons_chargement b WHERE b.id=?""",
            (bon_id,),
        ).fetchone()
        if bon is None:
            raise ValueError("Le bon de chargement sélectionné n'existe pas.")
        if bon["statut"] not in ("Validé", "Annulé"):
            raise ValueError("Le statut du bon ne permet pas sa suppression.")

        lignes = conn.execute(
            """SELECT lc.produit_id, lc.quantite_colis, lc.quantite_pieces,
                      p.designation, p.stock_actuel,
                      COALESCE(sc.quantite_colis, 0) AS camion_colis,
                      COALESCE(sc.quantite_pieces, 0) AS camion_pieces
               FROM lignes_chargement lc
               JOIN produits p ON p.id=lc.produit_id
               LEFT JOIN stock_camion_vendeur sc
                 ON sc.vendeur_id=? AND sc.produit_id=lc.produit_id
               WHERE lc.chargement_id=?""",
            (bon["vendeur_id"], bon_id),
        ).fetchall()
        if bon["statut"] == "Validé" and not lignes:
            raise ValueError("Le bon ne contient aucune ligne à supprimer.")

        if bon["statut"] == "Validé":
            for ligne in lignes:
                colis = float(ligne["quantite_colis"] or 0)
                pieces = float(ligne["quantite_pieces"] or 0)
                if (colis > float(ligne["camion_colis"] or 0) + 1e-9
                        or pieces > float(ligne["camion_pieces"] or 0) + 1e-9):
                    raise ValueError(
                        f"Suppression impossible pour {ligne['designation']} : "
                        "le stock disponible dans le camion ne permet pas de retourner "
                        "toute la quantité du bon au dépôt."
                    )

            for ligne in lignes:
                pieces = float(ligne["quantite_pieces"] or 0)
                conn.execute(
                    "UPDATE produits SET stock_actuel=stock_actuel+? WHERE id=?",
                    (pieces, ligne["produit_id"]),
                )
                conn.execute(
                    """UPDATE stock_camion_vendeur
                       SET quantite_colis=MAX(0, quantite_colis-?),
                           quantite_pieces=MAX(0, quantite_pieces-?),
                           date_maj=datetime('now')
                       WHERE vendeur_id=? AND produit_id=?""",
                    (
                        float(ligne["quantite_colis"] or 0),
                        pieces,
                        bon["vendeur_id"],
                        ligne["produit_id"],
                    ),
                )

        conn.execute("DELETE FROM lignes_chargement WHERE chargement_id=?", (bon_id,))
        mouvements_supprimes = supprimer_mouvements_document(
            conn, "bon_chargement", bon_id
        )
        conn.execute("DELETE FROM bons_chargement WHERE id=?", (bon_id,))

    return {
        "id": bon_id,
        "numero": bon["numero"],
        "mouvements_supprimes": mouvements_supprimes,
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
