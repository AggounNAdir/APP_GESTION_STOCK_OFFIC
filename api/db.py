"""
Accès base de données pour l'API.
⚠️ IMPORTANT : l'API utilise EXACTEMENT la même base SQLite (gestion_stock.db)
que l'application bureau (voir config.DB_PATH), pour rester la source de
vérité unique. Elle ajoute uniquement les colonnes/tables nécessaires au
portail client (mot de passe client, commandes en ligne).
"""
import os
import sys
import sqlite3

# S'assure que la racine du projet (où se trouve config.py, database.py, modules/)
# est bien sur le sys.path, quel que soit le répertoire depuis lequel l'API est lancée.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import DB_PATH  # noqa: E402  (chemin de la base, réutilisé tel quel)


def get_conn() -> sqlite3.Connection:
    """
    Retourne une connexion SQLite configurée.
    ✅ check_same_thread=False : FastAPI exécute les dépendances synchrones
    (get_db) dans un threadpool, et l'ouverture (__enter__) / fermeture
    (__exit__) d'une dépendance générateur peuvent être exécutées sur des
    threads différents du pool. Comme chaque requête obtient sa PROPRE
    connexion (aucun partage entre requêtes), ceci reste sûr.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def run_api_migrations() -> None:
    """
    Ajoute les colonnes/tables nécessaires au portail client, sans jamais
    toucher aux tables métier existantes. Idempotent (sûr à ré-exécuter).
    """
    conn = get_conn()
    try:
        c = conn.cursor()

        # --- Authentification portail sur la table clients existante ---
        c.execute("PRAGMA table_info(clients)")
        cols = [row[1] for row in c.fetchall()]
        if "password_hash" not in cols:
            c.execute("ALTER TABLE clients ADD COLUMN password_hash TEXT")
        if "portail_actif" not in cols:
            # Un client doit être explicitement activé par le personnel
            # avant de pouvoir se connecter au portail (sécurité par défaut).
            c.execute("ALTER TABLE clients ADD COLUMN portail_actif INTEGER DEFAULT 0")


        # --- S'assurer que la table produits a la colonne supprime si absente ---
        c.execute("PRAGMA table_info(produits)")
        prod_cols = [row[1] for row in c.fetchall()]
        if "supprime" not in prod_cols:
            try:
                c.execute("ALTER TABLE produits ADD COLUMN supprime INTEGER DEFAULT 0")
            except Exception:
                pass

        # --- Vendeurs (pour la supervision commerciale) ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS vendeurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                tel TEXT,
                actif INTEGER DEFAULT 1
            )
        """)
        
        # --- Colonnes optionnelles si absentes ---
        c.execute("PRAGMA table_info(bons_vente)")
        bv_cols = [row[1] for row in c.fetchall()]
        if "vendeur_id" not in bv_cols:
            c.execute("ALTER TABLE bons_vente ADD COLUMN vendeur_id INTEGER")
            c.execute("ALTER TABLE bons_vente ADD COLUMN montant_verse REAL DEFAULT 0.0")
            c.execute("ALTER TABLE bons_vente ADD COLUMN reste_payer REAL DEFAULT 0.0")

        c.execute("PRAGMA table_info(versements_clients)")
        vers_cols = [row[1] for row in c.fetchall()]
        if "vendeur_id" not in vers_cols:
            c.execute("ALTER TABLE versements_clients ADD COLUMN vendeur_id INTEGER")

        c.execute("PRAGMA table_info(commandes_clients)")
        cmd_cols = [row[1] for row in c.fetchall()]
        if "vendeur_id" not in cmd_cols:
            c.execute("ALTER TABLE commandes_clients ADD COLUMN vendeur_id INTEGER")

        # --- Commandes passées depuis le portail client ---
        # Une commande n'est PAS un bon de vente : elle reste "En attente"
        # jusqu'à validation par le personnel, qui la transforme en vente
        # réelle via l'application bureau (contrôle humain sur le stock/prix).
        c.execute("""
            CREATE TABLE IF NOT EXISTS commandes_clients (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          TEXT UNIQUE NOT NULL,
                client_id       INTEGER NOT NULL,
                vendeur_id      INTEGER,
                date_commande   TEXT NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'En attente',
                total_estime    REAL DEFAULT 0,
                observations    TEXT,
                bon_vente_id    INTEGER,
                FOREIGN KEY(client_id) REFERENCES clients(id),
                FOREIGN KEY(bon_vente_id) REFERENCES bons_vente(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS lignes_commande_client (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                commande_id     INTEGER NOT NULL,
                produit_id      INTEGER NOT NULL,
                quantite        REAL NOT NULL,
                prix_unitaire_estime REAL NOT NULL,
                total_estime    REAL NOT NULL,
                FOREIGN KEY(commande_id) REFERENCES commandes_clients(id),
                FOREIGN KEY(produit_id) REFERENCES produits(id)
            )
        """)

        conn.commit()
    finally:
        conn.close()

"""
Accès base de données pour l'API.
⚠️ IMPORTANT : l'API utilise EXACTEMENT la même base SQLite (gestion_stock.db)
que l'application bureau (voir config.DB_PATH), pour rester la source de
vérité unique. Elle ajoute uniquement les colonnes/tables nécessaires au
portail client (mot de passe client, commandes en ligne).
"""
import os
import sys
import sqlite3

# S'assure que la racine du projet (où se trouve config.py, database.py, modules/)
# est bien sur le sys.path, quel que soit le répertoire depuis lequel l'API est lancée.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import DB_PATH  # noqa: E402  (chemin de la base, réutilisé tel quel)


def get_conn() -> sqlite3.Connection:
    """
    Retourne une connexion SQLite configurée.
    ✅ check_same_thread=False : FastAPI exécute les dépendances synchrones
    (get_db) dans un threadpool, et l'ouverture (__enter__) / fermeture
    (__exit__) d'une dépendance générateur peuvent être exécutées sur des
    threads différents du pool. Comme chaque requête obtient sa PROPRE
    connexion (aucun partage entre requêtes), ceci reste sûr.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def run_api_migrations() -> None:
    """
    Ajoute les colonnes/tables nécessaires au portail client, sans jamais
    toucher aux tables métier existantes. Idempotent (sûr à ré-exécuter).
    """
    conn = get_conn()
    try:
        c = conn.cursor()

        # --- Authentification portail sur la table clients existante ---
        c.execute("PRAGMA table_info(clients)")
        cols = [row[1] for row in c.fetchall()]
        if "password_hash" not in cols:
            c.execute("ALTER TABLE clients ADD COLUMN password_hash TEXT")
        if "portail_actif" not in cols:
            c.execute("ALTER TABLE clients ADD COLUMN portail_actif INTEGER DEFAULT 0")


        # --- S'assurer que la table produits a la colonne supprime si absente ---
        c.execute("PRAGMA table_info(produits)")
        prod_cols = [row[1] for row in c.fetchall()]
        if "supprime" not in prod_cols:
            try:
                c.execute("ALTER TABLE produits ADD COLUMN supprime INTEGER DEFAULT 0")
            except Exception:
                pass

        # --- Vendeurs (pour la supervision commerciale) ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS vendeurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                tel TEXT,
                actif INTEGER DEFAULT 1
            )
        """)
        
        # --- Colonnes optionnelles si absentes ---
        c.execute("PRAGMA table_info(bons_vente)")
        bv_cols = [row[1] for row in c.fetchall()]
        if "vendeur_id" not in bv_cols:
            c.execute("ALTER TABLE bons_vente ADD COLUMN vendeur_id INTEGER")
            c.execute("ALTER TABLE bons_vente ADD COLUMN montant_verse REAL DEFAULT 0.0")
            c.execute("ALTER TABLE bons_vente ADD COLUMN reste_payer REAL DEFAULT 0.0")

        c.execute("PRAGMA table_info(versements_clients)")
        vers_cols = [row[1] for row in c.fetchall()]
        if "vendeur_id" not in vers_cols:
            c.execute("ALTER TABLE versements_clients ADD COLUMN vendeur_id INTEGER")

        c.execute("PRAGMA table_info(commandes_clients)")
        cmd_cols = [row[1] for row in c.fetchall()]
        if "vendeur_id" not in cmd_cols:
            c.execute("ALTER TABLE commandes_clients ADD COLUMN vendeur_id INTEGER")

        # --- Tables si inexistantes ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS commandes_clients (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          TEXT UNIQUE NOT NULL,
                client_id       INTEGER NOT NULL,
                vendeur_id      INTEGER,
                date_commande   TEXT NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'En attente',
                total_estime    REAL DEFAULT 0,
                observations    TEXT,
                bon_vente_id    INTEGER,
                FOREIGN KEY(client_id) REFERENCES clients(id),
                FOREIGN KEY(bon_vente_id) REFERENCES bons_vente(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS lignes_commande_client (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                commande_id     INTEGER NOT NULL,
                produit_id      INTEGER NOT NULL,
                quantite        REAL NOT NULL,
                prix_unitaire_estime REAL NOT NULL,
                total_estime    REAL NOT NULL,
                FOREIGN KEY(commande_id) REFERENCES commandes_clients(id),
                FOREIGN KEY(produit_id) REFERENCES produits(id)
            )
        """)

        conn.commit()
    finally:
        conn.close()

