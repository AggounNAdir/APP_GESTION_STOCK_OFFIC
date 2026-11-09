import os
import sqlite3

import pytest
from fastapi import HTTPException

from api import backup_service, rate_limit
from api.security import (
    create_vendeur_token, decode_vendeur_token, nouveau_sel_session,
)


@pytest.fixture
def base_temp(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES ('a')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(backup_service, "DB_PATH", str(db))
    monkeypatch.setattr(backup_service, "BACKUP_DIR", str(tmp_path / "bk"))
    return db


def test_sauvegarde_creee_et_valide(base_temp):
    chemin = backup_service.creer_sauvegarde("test")
    assert os.path.isfile(chemin)
    c = sqlite3.connect(chemin)
    assert c.execute("SELECT v FROM t").fetchone()[0] == "a"
    c.close()


def test_purge_garde_keep(base_temp, monkeypatch):
    monkeypatch.setattr(backup_service, "KEEP", 2)
    for i in range(4):
        # noms distincts même dans la même seconde
        backup_service.creer_sauvegarde(f"m{i}")
    assert len(backup_service.lister_sauvegardes()) == 2


def test_restauration(base_temp):
    chemin = backup_service.creer_sauvegarde("avant")
    c = sqlite3.connect(base_temp)
    c.execute("DELETE FROM t")
    c.commit()
    c.close()
    backup_service.restaurer_sauvegarde(os.path.basename(chemin))
    c = sqlite3.connect(base_temp)
    assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    c.close()


def test_jeton_vendeur_contient_le_sel():
    sel = nouveau_sel_session()
    payload = decode_vendeur_token(create_vendeur_token(1, "V1", sel))
    assert payload["sv"] == sel


def test_sels_differents():
    assert nouveau_sel_session() != nouveau_sel_session()


def test_limiteur_bloque_apres_5_echecs():
    cle = "test:limiteur"
    rate_limit.effacer_echecs(cle)
    for _ in range(rate_limit.MAX_ESSAIS):
        rate_limit.verifier_tentatives(cle)
        rate_limit.enregistrer_echec(cle)
    with pytest.raises(HTTPException) as exc:
        rate_limit.verifier_tentatives(cle)
    assert exc.value.status_code == 429
    rate_limit.effacer_echecs(cle)