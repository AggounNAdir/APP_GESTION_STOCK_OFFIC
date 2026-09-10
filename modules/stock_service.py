from modules.core import *

"""
Module métier : Logique des stocks, calcul PMP, mouvements et transactions.
Séparé de l'Interface Graphique (UI).
"""

import sqlite3
from config import DB_PATH

def get_conn():
    """Retourne une connexion SQLite configurée"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def calculer_pmp(conn, produit_id, nouvelle_quantite, nouveau_prix_achat,
                 stock_actuel_override=None, cout_actuel_override=None):
    """
    Calcule le nouveau PMP avec gestion des cas extrêmes et stock négatif.
    """
    if stock_actuel_override is not None:
        stock_actuel = float(stock_actuel_override)
        cout_actuel = float(cout_actuel_override or 0)
    else:
        cursor = conn.execute(
            "SELECT stock_actuel, cout_total_stock, prix_moyen_pondere FROM produits WHERE id=?",
            (produit_id,)
        )
        produit = cursor.fetchone()
        if not produit:
            return nouveau_prix_achat, nouvelle_quantite * nouveau_prix_achat
        stock_actuel = float(produit["stock_actuel"] or 0)
        cout_actuel = float(produit["cout_total_stock"] or 0)
    
    if stock_actuel <= 0:
        nouveau_cout_total = nouvelle_quantite * nouveau_prix_achat
        nouveau_stock_total = nouvelle_quantite
        if nouveau_stock_total > 0:
            nouveau_pmp = nouveau_cout_total / nouveau_stock_total
        else:
            nouveau_pmp = nouveau_prix_achat
    else:
        nouveau_cout_total = cout_actuel + (nouvelle_quantite * nouveau_prix_achat)
        nouveau_stock_total = stock_actuel + nouvelle_quantite
        
        if nouveau_stock_total > 0:
            nouveau_pmp = nouveau_cout_total / nouveau_stock_total
        else:
            nouveau_pmp = nouveau_prix_achat
    
    return nouveau_pmp, nouveau_cout_total

def recalculer_cout_stock_apres_sortie(conn, produit_id, quantite_sortie):
    """Recalcule le coût du stock et le PMP après une sortie (vente)"""
    produit = conn.execute(
        "SELECT stock_actuel, cout_total_stock, prix_moyen_pondere FROM produits WHERE id=?",
        (produit_id,)
    ).fetchone()
    
    if not produit:
        return
    
    stock_actuel = produit["stock_actuel"] or 0
    cout_actuel = produit["cout_total_stock"] or 0
    pmp = produit["prix_moyen_pondere"] or 0
    
    if pmp <= 0 and stock_actuel > 0:
        pmp = cout_actuel / stock_actuel
    
    reduction = quantite_sortie * pmp
    nouveau_cout = max(0.0, cout_actuel - reduction)
    nouveau_stock = max(0.0, stock_actuel - quantite_sortie)
    
    if nouveau_stock > 0:
        nouveau_pmp = nouveau_cout / nouveau_stock
    else:
        nouveau_pmp = 0
    
    conn.execute(
        "UPDATE produits SET stock_actuel = ?, prix_moyen_pondere = ?, cout_total_stock = ? WHERE id=?",
        (nouveau_stock, nouveau_pmp, nouveau_cout, produit_id)
    )

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
        for l in lignes_panier:
            prod = conn.execute("SELECT stock_actuel, designation FROM produits WHERE id=?", (l["produit_id"],)).fetchone()
            if not prod:
                raise Exception(f"Produit ID {l['produit_id']} introuvable.")
            
            facteur = float(l.get("facteur", 1) or 1)
            qty_base = l["quantite"] * facteur
            
            if qty_base > prod["stock_actuel"]:
                raise Exception(f"Stock insuffisant pour '{prod['designation']}'. Disponible: {prod['stock_actuel']}, Demandé: {qty_base}")

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
            recalculer_cout_stock_apres_sortie(conn, l["produit_id"], qty_base)
            
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
