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

    ⚠️ Les tables sont TOUJOURS créées (CREATE TABLE IF NOT EXISTS) AVANT
    toute tentative d'ALTER TABLE dessus : sur une base neuve où l'app
    bureau n'a pas encore tourné, altérer une colonne d'une table qui
    n'existe pas encore provoquerait une erreur SQL et empêcherait l'API
    de démarrer.
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

        # --- Créer d'abord TOUTES les tables portail si absentes ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS vendeurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                tel TEXT,
                actif INTEGER DEFAULT 1
            )
        """)
        c.execute("PRAGMA table_info(vendeurs)")
        vd_cols = [row[1] for row in c.fetchall()]
        if "password_hash" not in vd_cols:
            c.execute("ALTER TABLE vendeurs ADD COLUMN password_hash TEXT")

        # Filet de sécurité si l'API démarre avant l'app bureau : normalement
        # créée par modules/core.py (init_db), mais on ne veut pas planter ici.
        c.execute("""
            CREATE TABLE IF NOT EXISTS versements_clients (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                numero      TEXT UNIQUE NOT NULL,
                date_vers   TEXT NOT NULL,
                client_id   INTEGER NOT NULL,
                montant     REAL NOT NULL,
                mode        TEXT DEFAULT 'Espèces',
                reference   TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """)
        # --- Tables dédiées aux commandes des prospects (totalement isolées) ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS commandes_prospects (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          TEXT UNIQUE NOT NULL,
                prospect_id     INTEGER NOT NULL,
                vendeur_id      INTEGER,
                date_commande   TEXT NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'En attente',
                montant_total   REAL DEFAULT 0,
                observations    TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS lignes_commande_prospect (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                commande_id     INTEGER NOT NULL,
                produit_id      INTEGER NOT NULL,
                quantite        REAL NOT NULL,
                prix_unitaire   REAL NOT NULL,
                total           REAL NOT NULL,
                FOREIGN KEY(commande_id) REFERENCES commandes_prospects(id),
                FOREIGN KEY(produit_id) REFERENCES produits(id)
            )
        """)
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

        # --- Pointages GPS de visite (tournée terrain Silwane Androway) ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS tournee_pointages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id       INTEGER,
                vendeur_id      INTEGER,
                code_client     TEXT,
                nom_client      TEXT,
                latitude        REAL,
                longitude       REAL,
                date_pointage   TEXT NOT NULL,
                observations    TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """)

        # --- Prospects saisis sur le terrain (pas encore des clients validés) ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS prospects_clients (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT UNIQUE NOT NULL,
                nom             TEXT NOT NULL,
                tel             TEXT,
                adresse         TEXT,
                wilaya          TEXT,
                latitude        REAL,
                longitude       REAL,
                vendeur_id      INTEGER,
                date_creation   TEXT NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'Nouveau',
                client_id       INTEGER
            )
        """)
        # --- PROSPECTS CRÉÉS PAR LES VENDEURS ANDROWAY ---
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS prospects_vendeurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                vendeur_id INTEGER,
                tel TEXT,
                adresse TEXT,
                ville TEXT,
                solde REAL DEFAULT 0.0,
                date_creation TEXT NOT NULL,
                FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id)
            )
        """
        )

        # --- VERSEMENTS EFFECTUÉS SUR LES PROSPECTS TERRAIN ---
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS versements_prospects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                date_vers TEXT NOT NULL,
                prospect_id INTEGER NOT NULL,
                vendeur_id INTEGER,
                montant REAL NOT NULL,
                mode TEXT DEFAULT 'Espèces',
                reference TEXT,
                FOREIGN KEY(prospect_id) REFERENCES prospects_vendeurs(id),
                FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id)
            )
        """
        )
        # --- Colonnes optionnelles si absentes (les tables existent désormais) ---
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

        # --- Signature électronique du bon de livraison (BL = bon de vente) ---
        if "signature_bl" not in bv_cols:
            c.execute("ALTER TABLE bons_vente ADD COLUMN signature_bl TEXT")
        if "signataire_nom" not in bv_cols:
            c.execute("ALTER TABLE bons_vente ADD COLUMN signataire_nom TEXT")
        if "date_signature" not in bv_cols:
            c.execute("ALTER TABLE bons_vente ADD COLUMN date_signature TEXT")

        conn.commit()
    finally:
        conn.close()