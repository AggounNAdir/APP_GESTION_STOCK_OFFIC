"""
Base de données UNIQUE de l'application (API + application bureau).

⚠️ SOURCE DE VÉRITÉ : ce module est le SEUL endroit où l'emplacement de la
base SQLite est défini. Le fichier physique se trouve dans le dossier `api/` :

    api/gestion_stock.db

Tout le reste du projet (config.py, modules/core.py, database.py, scripts...)
importe `DB_PATH` depuis ici. Le chemin est absolu : il ne dépend donc plus du
dossier depuis lequel l'API ou l'application bureau est lancée.

Options :
  • Variable d'environnement GESTION_STOCK_DB : chemin absolu alternatif
    (utile pour les tests ou un déploiement avec un volume dédié).
  • Application gelée (PyInstaller / .exe) : <dossier de l'exe>/api/gestion_stock.db

Ce module fournit aussi les DEUX seules portes d'entrée vers la base :
  • get_conn()  : connexion SQLite configurée (utilisée par le bureau ET l'API)
  • init_db()   : création/migration de TOUTES les tables (voir api/schema.py)
Ne pas recréer de get_conn()/init_db() ailleurs : importer celles-ci.
"""
import logging
import os
import sqlite3
import sys

# Racine du projet (où se trouvent config.py, database.py, modules/) et dossier api/.
API_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(API_DIR)

# S'assure que la racine du projet est sur le sys.path, quel que soit le
# répertoire depuis lequel l'API est lancée.
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DB_FILENAME = "gestion_stock.db"
_log = logging.getLogger("api.db")


def _app_dir() -> str:
    """Dossier de l'application : dossier de l'exe (gelé) ou racine du projet."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return PROJECT_ROOT


def _resolve_db_path() -> str:
    override = os.environ.get("GESTION_STOCK_DB", "").strip()
    if override:
        return os.path.abspath(override)
    if getattr(sys, "frozen", False):
        return os.path.join(_app_dir(), "api", DB_FILENAME)
    return os.path.join(API_DIR, DB_FILENAME)


# ✅ Chemin UNIQUE et absolu de la base de données.
DB_PATH = _resolve_db_path()


def _adopt_legacy_database() -> None:
    """
    Reprise automatique de l'ancienne base (gestion_stock.db à la racine du
    projet, à côté de l'exe, ou dans le dossier courant) vers api/.

    - Ne s'exécute que si la nouvelle base n'existe pas encore.
    - COPIE (API de sauvegarde SQLite, sûre même en mode WAL) : l'ancien
      fichier n'est ni modifié ni supprimé.
    """
    if os.path.exists(DB_PATH):
        return

    candidates = []
    for base in (_app_dir(), os.getcwd()):
        path = os.path.abspath(os.path.join(base, DB_FILENAME))
        if path != DB_PATH and path not in candidates:
            candidates.append(path)

    for legacy in candidates:
        if os.path.isfile(legacy) and os.path.getsize(legacy) > 0:
            try:
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                src = sqlite3.connect(legacy)
                dst = sqlite3.connect(DB_PATH)
                try:
                    src.backup(dst)
                finally:
                    dst.close()
                    src.close()
                _log.info("Base reprise depuis %s vers %s", legacy, DB_PATH)
            except Exception as exc:  # ne jamais empêcher le démarrage
                _log.error("Reprise de l'ancienne base impossible (%s) : %s", legacy, exc)
                try:
                    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) == 0:
                        os.remove(DB_PATH)
                except OSError:
                    pass
            return


os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
_adopt_legacy_database()


def get_conn() -> sqlite3.Connection:
    """
    Retourne une connexion SQLite configurée (unique pour bureau + API).
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


def init_db() -> None:
    """
    Crée / met à niveau TOUTES les tables de la base unique (métier, portail
    client, tournée terrain). Idempotent : sûr à appeler à chaque démarrage,
    depuis l'application bureau comme depuis l'API, dans n'importe quel ordre
    (l'API peut démarrer sur une base vierge).

    Lève une exception si la création échoue (l'API ne doit pas démarrer sur
    un schéma incomplet). Le bureau l'appelle via modules.core.init_db, qui
    journalise l'erreur sans fermer l'application.
    """
    from api.schema import init_schema  # import local : évite tout cycle

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        init_schema(conn)
    except Exception:
        conn.rollback()
        _log.exception("Échec de l'initialisation de la base %s", DB_PATH)
        raise
    finally:
        conn.close()


# Ancien nom conservé pour compatibilité (api/main.py, set_password.py, tests...).
run_api_migrations = init_db
