"""Sauvegarde sûre de la base SQLite (API backup, compatible mode WAL)."""
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime

from api.db import DB_PATH, API_DIR

_log = logging.getLogger("api.backup")

BACKUP_DIR = os.environ.get("GESTION_STOCK_BACKUP_DIR", os.path.join(API_DIR, "backups"))
KEEP = int(os.environ.get("GESTION_STOCK_BACKUP_KEEP", "14"))


def creer_sauvegarde(motif: str = "auto") -> str:
    """Copie la base, vérifie la copie, purge les anciennes. Retourne le chemin."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    nom = f"gestion_stock_{datetime.now():%Y%m%d_%H%M%S}_{motif}.db"
    dest = os.path.join(BACKUP_DIR, nom)

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    chk = sqlite3.connect(dest)
    try:
        resultat = chk.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        chk.close()
    if resultat != "ok":
        os.remove(dest)
        raise RuntimeError(f"Sauvegarde corrompue (supprimée) : {resultat}")

    _purger()
    _log.info("Sauvegarde créée : %s", dest)
    return dest


def _purger() -> None:
    fichiers = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith(".db"))
    for f in fichiers[:-KEEP]:
        try:
            os.remove(os.path.join(BACKUP_DIR, f))
        except OSError:
            _log.warning("Impossible de supprimer %s", f)


def lister_sauvegardes() -> list:
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted((f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")), reverse=True)


def restaurer_sauvegarde(nom_fichier: str) -> None:
    """À appeler API ARRÊTÉE. Sauvegarde d'abord l'état actuel, puis restaure."""
    source = os.path.join(BACKUP_DIR, os.path.basename(nom_fichier))
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    chk = sqlite3.connect(source)
    try:
        if chk.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Sauvegarde invalide, restauration refusée")
    finally:
        chk.close()
    creer_sauvegarde("avant_restauration")
    src = sqlite3.connect(source)
    dst = sqlite3.connect(DB_PATH)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def demarrer_planificateur(heures: int = 24) -> None:
    def boucle():
        while True:
            time.sleep(heures * 3600)
            try:
                creer_sauvegarde("auto")
            except Exception:
                _log.exception("Sauvegarde automatique échouée")

    threading.Thread(target=boucle, daemon=True, name="backup-auto").start()