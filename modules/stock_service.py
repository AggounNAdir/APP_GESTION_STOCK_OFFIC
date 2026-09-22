from modules.core import *

"""
Module métier : Logique des stocks, calcul PMP, mouvements et transactions.
Séparé de l'Interface Graphique (UI).
"""

import sqlite3
from config import DB_PATH

# ✅ CORRECTION : on ne redéfinit plus ces fonctions ici. On réutilise les
# implémentations de modules/core.py (celles réellement utilisées par le
# reste de l'application : bondialog.py, ventecomptoirdialog.py, ...) pour
# garantir qu'une même opération (vente, entrée/sortie de stock) produit
# toujours le même résultat métier, quel que soit le point d'entrée utilisé.
from modules.core import calculer_pmp, recalculer_cout_stock_apres_sortie  # noqa: F401

from api.db import get_conn  # noqa: E402,F401  (connexion unique)

def valider_transaction_vente(client_id, total, lignes_panier, montant_recu=0):
    """
    Logique métier pure pour valider une vente :
    - Vérifie le stock disponible pour chaque ligne.
    - Insère le bon de vente et les lignes.
    - Met à jour les stocks (PMP / coût).
    - Met à jour le solde client (sauf COMPTOIR).
    - Enregistre la transaction.
    """
    conn = get_conn()
    try:
        # 1. Vérification des stocks
        # ✅ CORRECTION : on cumule d'abord les quantités par produit (un même
        # produit peut apparaître sur plusieurs lignes du panier) avant de
        # comparer au stock disponible, pour éviter toute survente.
        besoins = {}
        for l in lignes_panier:
            facteur = float(l.get("facteur", 1) or 1)
            qty_base = l["quantite"] * facteur
            besoins[l["produit_id"]] = besoins.get(l["produit_id"], 0) + qty_base

        for produit_id, qty_demandee in besoins.items():
            prod = conn.execute("SELECT stock_actuel, designation FROM produits WHERE id=?", (produit_id,)).fetchone()
            if not prod:
                raise Exception(f"Produit ID {produit_id} introuvable.")

            if qty_demandee > (prod["stock_actuel"] or 0):
                raise Exception(f"Stock insuffisant pour '{prod['designation']}'. Disponible: {prod['stock_actuel']}, Demandé: {qty_demandee}")

        # 2. Insertion bon de vente
        from utils import next_numero_tiers
        from datetime import date
        
        num = next_numero_tiers("BV", client_id)
        dt = date.today().strftime("%Y-%m-%d")
        
        conn.execute(
            "INSERT INTO bons_vente(numero, date_bon, client_id, total, statut) VALUES(?,?,?,?,?)",
            (num, dt, client_id, total, "Validé")
        )
        bon_id = conn.execute("SELECT id FROM bons_vente WHERE numero=?", (num,)).fetchone()["id"]
        
        # 3. Insertion lignes & mise à jour stock
        for l in lignes_panier:
            facteur = float(l.get("facteur", 1) or 1)
            qty_base = l["quantite"] * facteur
            
            conn.execute(
                "INSERT INTO lignes_vente(bon_id, produit_id, quantite, prix_unitaire, total) VALUES(?,?,?,?,?)",
                (bon_id, l["produit_id"], qty_base, l["prix"], l["total"])
            )
            recalculer_cout_stock_apres_sortie(
                conn, l["produit_id"], qty_base,
                type_mouvement="VENTE", document_type="bon_vente",
                document_id=bon_id, date_document=dt,
            )
            
        # 4. Solde client (si non COMPTOIR)
        client = conn.execute("SELECT nom FROM clients WHERE id=?", (client_id,)).fetchone()
        if client and client["nom"] != "COMPTOIR":
            conn.execute(
                "UPDATE clients SET solde = solde + ? WHERE id=?", (total, client_id)
            )
            
        conn.commit()
        return True, num
    except Exception as ex:
        conn.rollback()
        return False, str(ex)
    finally:
        conn.close()