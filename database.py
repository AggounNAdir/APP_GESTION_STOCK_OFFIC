"""
Gestion de la base de données, connexions, PMP et initialisation des tables.
"""

import sqlite3
import os
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
    Calcule le nouveau PMP avec gestion des cas extrêmes
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
    """Recalcule le coût du stock après une sortie"""
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

def init_db():
    """Initialise toutes les tables de la base de données si elles n'existent pas"""
    conn = get_conn()
    c = conn.cursor()
    
    c.executescript("""
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE IF NOT EXISTS produits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            code_barre  TEXT,
            designation TEXT NOT NULL,
            marque      TEXT,
            unite       TEXT DEFAULT 'Pièce',
            facteur_conversion REAL DEFAULT 1,
            prix_achat  REAL DEFAULT 0,
            prix_vente  REAL DEFAULT 0,
            stock_actuel REAL DEFAULT 0,
            stock_min   REAL DEFAULT 0,
            actif       INTEGER DEFAULT 1,
            prix_moyen_pondere REAL DEFAULT 0,
            cout_total_stock REAL DEFAULT 0,
            tva         REAL DEFAULT 19,
            prix_gros   REAL DEFAULT 0,
            prix_detail REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS clients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT NOT NULL,
            telephone   TEXT,
            adresse     TEXT,
            solde       REAL DEFAULT 0,
            type_client TEXT DEFAULT 'Détail',
            nif         TEXT,
            nis         TEXT,
            rc          TEXT,
            art         TEXT
        );

        CREATE TABLE IF NOT EXISTS fournisseurs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT NOT NULL,
            telephone   TEXT,
            adresse     TEXT,
            solde       REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bons_vente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            date_bon    TEXT NOT NULL,
            client_id   INTEGER NOT NULL,
            total       REAL NOT NULL,
            statut      TEXT DEFAULT 'Validé',
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS lignes_vente (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bon_id      INTEGER NOT NULL,
            produit_id  INTEGER NOT NULL,
            quantite    REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            total       REAL NOT NULL,
            FOREIGN KEY(bon_id) REFERENCES bons_vente(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id)
        );

        CREATE TRIGGER IF NOT EXISTS update_client_solde_after_bon_vente
        AFTER INSERT ON bons_vente
        BEGIN
            UPDATE clients 
            SET solde = solde + NEW.total 
            WHERE id = NEW.client_id;
        END;
    """)
    conn.commit()
    conn.close()
