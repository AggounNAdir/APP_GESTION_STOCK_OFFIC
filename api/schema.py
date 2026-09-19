"""
SCHÉMA UNIQUE de la base de données (application bureau + API).

⚠️ C'est le SEUL endroit du projet où les tables sont créées et migrées.
Avant, la création des tables était dupliquée à plusieurs endroits
(modules/core.py, api/db.py, database.py, modules/versementpage.py,
api/routers/commandes.py, api/routers/versements.py, prix_niveaux.py),
avec des définitions différentes pour une même table : c'était la première
qui s'exécutait qui "gagnait". Désormais tout passe par init_schema().

Utilisation (ne pas appeler directement, passer par api.db.init_db) :

    from api.db import init_db
    init_db()      # idempotent : sûr à appeler à chaque démarrage

Règles :
  • Nouvelle table   -> l'ajouter dans _creer_tables().
  • Nouvelle colonne -> l'ajouter dans _migrer_colonnes() via _ajouter_colonne()
    (les bases existantes sont mises à jour, les bases neuves aussi).
  • Ne JAMAIS faire de CREATE/ALTER TABLE ailleurs (pages, routers, scripts).
"""
import logging
import sqlite3

_log = logging.getLogger("api.schema")


# ═══════════════════════════ OUTILS ═══════════════════════════

def _colonnes(c: sqlite3.Cursor, table: str) -> list:
    c.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in c.fetchall()]


def _ajouter_colonne(c: sqlite3.Cursor, table: str, colonne: str, definition: str) -> bool:
    """
    Ajoute `colonne` à `table` si elle est absente. Retourne True si ajoutée.
    Tolère une exécution concurrente (bureau + API démarrés en même temps).
    """
    if colonne in _colonnes(c, table):
        return False
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {colonne} {definition}")
    except sqlite3.OperationalError as exc:
        if "duplicate column" in str(exc).lower():
            return False
        raise
    _log.info("Colonne '%s' ajoutée à la table '%s'", colonne, table)
    return True


# ═══════════════════════════ TABLES ═══════════════════════════

def _creer_tables(c: sqlite3.Cursor) -> None:
    """Crée TOUTES les tables (métier + portail client + tournée terrain)."""
    c.executescript("""
    PRAGMA foreign_keys = ON;

    -- ───────────── Métier : catalogue & tiers ─────────────
    CREATE TABLE IF NOT EXISTS produits (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT UNIQUE NOT NULL,
        barcode     TEXT UNIQUE,
        designation TEXT NOT NULL,
        unite       TEXT DEFAULT 'Pcs',
        facteur_conversion REAL DEFAULT 1,
        prix_achat  REAL DEFAULT 0,
        prix_vente  REAL DEFAULT 0,
        stock_actuel REAL DEFAULT 0,
        stock_min   REAL DEFAULT 0,
        actif       INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS clients (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        code    TEXT UNIQUE NOT NULL,
        nom     TEXT NOT NULL,
        adresse TEXT,
        tel     TEXT,
        email   TEXT,
        solde   REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS fournisseurs (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        code    TEXT UNIQUE NOT NULL,
        nom     TEXT NOT NULL,
        adresse TEXT,
        tel     TEXT,
        email   TEXT,
        solde   REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS prix_speciaux_clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        prix_special REAL NOT NULL,
        date_debut TEXT,
        date_fin TEXT,
        actif INTEGER DEFAULT 1,
        date_modification TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(produit_id) REFERENCES produits(id),
        UNIQUE(client_id, produit_id)
    );

    CREATE TABLE IF NOT EXISTS clients_niveau_prix (
        client_id   INTEGER PRIMARY KEY,
        niveau      TEXT DEFAULT 'detail',
        FOREIGN KEY(client_id) REFERENCES clients(id)
    );

    -- ───────────── Métier : achats ─────────────
    CREATE TABLE IF NOT EXISTS bons_achat (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero          TEXT UNIQUE NOT NULL,
        date_bon        TEXT NOT NULL,
        fournisseur_id  INTEGER NOT NULL,
        total           REAL DEFAULT 0,
        statut          TEXT DEFAULT 'Validé',
        date_creation   TEXT,
        date_livraison  TEXT,
        num_facture_fournisseur TEXT,
        num_bl_fournisseur TEXT,
        ancien_solde    REAL DEFAULT 0,
        nouveau_solde   REAL DEFAULT 0,
        FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
    );

    CREATE TABLE IF NOT EXISTS lignes_achat (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        bon_id      INTEGER NOT NULL,
        produit_id  INTEGER NOT NULL,
        quantite    REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        total       REAL NOT NULL,
        FOREIGN KEY(bon_id) REFERENCES bons_achat(id),
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );

    CREATE TABLE IF NOT EXISTS versements_fournisseurs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero          TEXT UNIQUE NOT NULL,
        date_vers       TEXT NOT NULL,
        fournisseur_id  INTEGER NOT NULL,
        montant         REAL NOT NULL,
        mode            TEXT DEFAULT 'Espèces',
        reference       TEXT,
        FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
    );

    CREATE TABLE IF NOT EXISTS retours_achat (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero          TEXT UNIQUE NOT NULL,
        date_retour     TEXT NOT NULL,
        bon_achat_id    INTEGER,
        fournisseur_id  INTEGER NOT NULL,
        total           REAL DEFAULT 0,
        motif           TEXT,
        FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
    );

    CREATE TABLE IF NOT EXISTS lignes_retour_achat (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        retour_id   INTEGER NOT NULL,
        produit_id  INTEGER NOT NULL,
        quantite    REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        total       REAL NOT NULL,
        FOREIGN KEY(retour_id) REFERENCES retours_achat(id)
    );

    -- ───────────── Métier : ventes ─────────────
    CREATE TABLE IF NOT EXISTS bons_vente (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        numero      TEXT UNIQUE NOT NULL,
        date_bon    TEXT NOT NULL,
        client_id   INTEGER NOT NULL,
        total       REAL DEFAULT 0,
        total_ht    REAL DEFAULT 0,
        tva_total   REAL DEFAULT 0,
        total_ttc   REAL DEFAULT 0,
        statut      TEXT DEFAULT 'Validé',
        observations TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    );

    CREATE TABLE IF NOT EXISTS lignes_vente (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        bon_id      INTEGER NOT NULL,
        produit_id  INTEGER NOT NULL,
        quantite    REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        total       REAL DEFAULT 0,
        total_ht    REAL DEFAULT 0,
        tva_taux    REAL DEFAULT 0,
        total_tva   REAL DEFAULT 0,
        total_ttc   REAL DEFAULT 0,
        FOREIGN KEY(bon_id) REFERENCES bons_vente(id),
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );

    CREATE TABLE IF NOT EXISTS factures (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero          TEXT UNIQUE NOT NULL,
        date_facture    TEXT NOT NULL,
        bon_vente_id    INTEGER NOT NULL,
        client_id       INTEGER NOT NULL,
        total_ht        REAL DEFAULT 0,
        tva             REAL DEFAULT 19,
        total_ttc       REAL DEFAULT 0,
        statut          TEXT DEFAULT 'Émise',
        date_echeance   TEXT,
        observations    TEXT,
        FOREIGN KEY(bon_vente_id) REFERENCES bons_vente(id),
        FOREIGN KEY(client_id) REFERENCES clients(id)
    );

    CREATE TABLE IF NOT EXISTS facture_tva_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facture_id INTEGER NOT NULL,
        taux_tva REAL NOT NULL,
        total_ht REAL NOT NULL,
        total_tva REAL NOT NULL,
        FOREIGN KEY(facture_id) REFERENCES factures(id)
    );

    CREATE TABLE IF NOT EXISTS versements_clients (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        numero      TEXT UNIQUE NOT NULL,
        date_vers   TEXT NOT NULL,
        client_id   INTEGER NOT NULL,
        montant     REAL NOT NULL,
        mode        TEXT DEFAULT 'Espèces',
        reference   TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    );

    CREATE TABLE IF NOT EXISTS retours_vente (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        numero      TEXT UNIQUE NOT NULL,
        date_retour TEXT NOT NULL,
        bon_vente_id INTEGER,
        client_id   INTEGER NOT NULL,
        total       REAL DEFAULT 0,
        motif       TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    );

    CREATE TABLE IF NOT EXISTS lignes_retour_vente (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        retour_id   INTEGER NOT NULL,
        produit_id  INTEGER NOT NULL,
        quantite    REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        total       REAL NOT NULL,
        FOREIGN KEY(retour_id) REFERENCES retours_vente(id)
    );

    CREATE TABLE IF NOT EXISTS remises (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        vente_id    INTEGER,
        type        TEXT,
        valeur      REAL,
        motif       TEXT,
        total_avant REAL,
        total_apres REAL,
        date_remise TEXT DEFAULT CURRENT_TIMESTAMP,
        produit_id  INTEGER,
        achat_id    INTEGER,
        reference   TEXT,
        FOREIGN KEY(vente_id) REFERENCES bons_vente(id)
    );

    CREATE TABLE IF NOT EXISTS historique_prix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        date_achat TEXT NOT NULL,
        quantite REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        prix_moyen_apres REAL,
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );

    CREATE TABLE IF NOT EXISTS profils_entreprise (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type_profil TEXT DEFAULT 'simple',
        adresse TEXT DEFAULT '',
        telephone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        site_web TEXT DEFAULT '',
        ville TEXT DEFAULT '',
        nif TEXT DEFAULT '',
        nis TEXT DEFAULT '',
        nrc TEXT DEFAULT '',
        art_imp TEXT DEFAULT '',
        registre_commerce TEXT DEFAULT '',
        capitale_social TEXT DEFAULT '',
        logo_path TEXT DEFAULT '',
        actif INTEGER DEFAULT 1,
        est_defaut INTEGER DEFAULT 0,
        date_creation TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- ───────────── Commerciaux / vendeurs & prospects (tournée terrain) ─────────────
    CREATE TABLE IF NOT EXISTS vendeurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        tel TEXT,
        actif INTEGER DEFAULT 1,
        password_hash TEXT
    );

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
        client_id       INTEGER,
        solde           REAL DEFAULT 0.0
    );

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
    );

    -- prospect_id désigne un prospects_clients.id (utilisé ainsi par
    -- VersementPage côté bureau ET par api/routers/versements.py).
    CREATE TABLE IF NOT EXISTS versements_prospects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        date_vers TEXT NOT NULL,
        prospect_id INTEGER NOT NULL,
        montant REAL NOT NULL,
        mode TEXT DEFAULT 'Espèces',
        reference TEXT,
        vendeur_id INTEGER,
        FOREIGN KEY(prospect_id) REFERENCES prospects_clients(id)
    );

    CREATE TABLE IF NOT EXISTS commandes_prospects (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero          TEXT UNIQUE NOT NULL,
        prospect_id     INTEGER NOT NULL,
        vendeur_id      INTEGER,
        date_commande   TEXT NOT NULL,
        statut          TEXT NOT NULL DEFAULT 'En attente',
        montant_total   REAL DEFAULT 0,
        observations    TEXT
    );

    CREATE TABLE IF NOT EXISTS lignes_commande_prospect (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id     INTEGER NOT NULL,
        produit_id      INTEGER NOT NULL,
        quantite        REAL NOT NULL,
        prix_unitaire   REAL NOT NULL,
        total           REAL NOT NULL,
        FOREIGN KEY(commande_id) REFERENCES commandes_prospects(id),
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );

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
    );

    -- ───────────── Portail client : commandes en ligne ─────────────
    -- Une commande n'est PAS un bon de vente : elle reste "En attente"
    -- jusqu'à validation par le personnel via l'application bureau.
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
    );

    CREATE TABLE IF NOT EXISTS lignes_commande_client (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id     INTEGER NOT NULL,
        produit_id      INTEGER NOT NULL,
        quantite        REAL NOT NULL,
        prix_unitaire_estime REAL NOT NULL,
        total_estime    REAL NOT NULL,
        FOREIGN KEY(commande_id) REFERENCES commandes_clients(id),
        FOREIGN KEY(produit_id) REFERENCES produits(id)
    );
    """)


# ═══════════════════════════ MIGRATIONS DE COLONNES ═══════════════════════════

def _migrer_colonnes(c: sqlite3.Cursor) -> None:
    """
    Met à niveau les bases EXISTANTES (créées par une ancienne version) et
    complète les bases neuves. Chaque ajout est idempotent.

    ⚠️ Ordre important : `produits` d'abord, car la migration de
    lignes_achat lit produits.tva (c'était la cause de l'erreur
    "no such column: p.tva" au premier démarrage sur base vierge).
    """
    # ── produits ──
    _ajouter_colonne(c, "produits", "barcode", "TEXT")
    _ajouter_colonne(c, "produits", "fournisseur", "TEXT")
    for col in ("prix_super_gros", "prix_gros", "prix_detail", "prix_special"):
        if _ajouter_colonne(c, "produits", col, "REAL DEFAULT 0"):
            c.execute(f"UPDATE produits SET {col} = prix_vente")
    _ajouter_colonne(c, "produits", "prix_moyen_pondere", "REAL DEFAULT 0")
    _ajouter_colonne(c, "produits", "cout_total_stock", "REAL DEFAULT 0")
    _ajouter_colonne(c, "produits", "tva", "REAL DEFAULT 19")
    _ajouter_colonne(c, "produits", "supprime", "INTEGER DEFAULT 0")

    # ── clients ──
    if _ajouter_colonne(c, "clients", "code", "TEXT"):
        c.execute("UPDATE clients SET code = 'CLT-' || id WHERE code IS NULL OR code = ''")
    for col in ("tel", "email", "nif", "nis", "nrc", "art_imp",
                "registre_commerce", "capitale_social", "ville"):
        _ajouter_colonne(c, "clients", col, "TEXT")
    _ajouter_colonne(c, "clients", "niveau_prix", "TEXT DEFAULT 'detail'")
    # Accès portail client (mot de passe + activation explicite par le personnel)
    _ajouter_colonne(c, "clients", "password_hash", "TEXT")
    _ajouter_colonne(c, "clients", "portail_actif", "INTEGER DEFAULT 0")

    # ── fournisseurs ──
    if _ajouter_colonne(c, "fournisseurs", "code", "TEXT"):
        c.execute("UPDATE fournisseurs SET code = 'FRN-' || id WHERE code IS NULL OR code = ''")
    for col in ("nis", "nrc", "art_imp", "registre_commerce", "capitale_social", "ville"):
        _ajouter_colonne(c, "fournisseurs", col, "TEXT")

    # ── achats ──
    if _ajouter_colonne(c, "lignes_achat", "tva_taux", "REAL DEFAULT 0"):
        c.execute("""UPDATE lignes_achat SET tva_taux = (
            SELECT COALESCE(p.tva, 19) FROM produits p WHERE p.id = lignes_achat.produit_id
        )""")
    if _ajouter_colonne(c, "lignes_achat", "total_ht", "REAL DEFAULT 0"):
        c.execute("UPDATE lignes_achat SET total_ht = total")
    if _ajouter_colonne(c, "lignes_achat", "total_ttc", "REAL DEFAULT 0"):
        c.execute("UPDATE lignes_achat SET total_ttc = total_ht * (1 + tva_taux / 100.0)")
    _ajouter_colonne(c, "bons_achat", "observations", "TEXT")

    # ── ventes ──
    _ajouter_colonne(c, "bons_vente", "observations", "TEXT")
    for col in ("total_ht", "tva_total", "total_ttc"):
        _ajouter_colonne(c, "bons_vente", col, "REAL DEFAULT 0")
    for col in ("total_ht", "tva_taux", "total_tva", "total_ttc"):
        _ajouter_colonne(c, "lignes_vente", col, "REAL DEFAULT 0")
    # Vendeur / encaissement
    _ajouter_colonne(c, "bons_vente", "vendeur_id", "INTEGER")
    _ajouter_colonne(c, "bons_vente", "montant_verse", "REAL DEFAULT 0.0")
    _ajouter_colonne(c, "bons_vente", "reste_payer", "REAL DEFAULT 0.0")
    # Signature électronique du bon de livraison (BL = bon de vente)
    _ajouter_colonne(c, "bons_vente", "signature_bl", "TEXT")
    _ajouter_colonne(c, "bons_vente", "signataire_nom", "TEXT")
    _ajouter_colonne(c, "bons_vente", "date_signature", "TEXT")

    # ── divers ──
    for col in ("produit_id", "achat_id"):
        _ajouter_colonne(c, "remises", col, "INTEGER")
    _ajouter_colonne(c, "remises", "reference", "TEXT")
    _ajouter_colonne(c, "prix_speciaux_clients", "date_modification", "TEXT")
    _ajouter_colonne(c, "versements_clients", "vendeur_id", "INTEGER")
    _ajouter_colonne(c, "commandes_clients", "vendeur_id", "INTEGER")
    _ajouter_colonne(c, "commandes_prospects", "montant_total", "REAL DEFAULT 0")
    _ajouter_colonne(c, "prospects_clients", "solde", "REAL DEFAULT 0.0")
    _ajouter_colonne(c, "vendeurs", "password_hash", "TEXT")


# ═══════════════════════════ DONNÉES DE BASE ═══════════════════════════

def _donnees_par_defaut(c: sqlite3.Cursor) -> None:
    """Client COMPTOIR (ventes au comptoir) : créé s'il n'existe pas."""
    c.execute("SELECT id FROM clients WHERE nom = 'COMPTOIR'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO clients(code, nom, adresse, tel, email, solde) VALUES(?, ?, ?, ?, ?, ?)",
            ("CLT-COMPTOIR", "COMPTOIR", "", "", "", 0),
        )


# ═══════════════════════════ POINT D'ENTRÉE ═══════════════════════════

def init_schema(conn: sqlite3.Connection) -> None:
    """Crée/migre l'ensemble du schéma sur `conn`, puis valide (commit)."""
    c = conn.cursor()
    _creer_tables(c)
    _migrer_colonnes(c)
    _donnees_par_defaut(c)
    conn.commit()
