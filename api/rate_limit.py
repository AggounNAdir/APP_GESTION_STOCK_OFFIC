"""Limiteur de tentatives de connexion (en mémoire)."""
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, status

_echecs = defaultdict(list)
_verrou = threading.Lock()

MAX_ESSAIS = 5            # par ip + identifiant
MAX_ESSAIS_IP = 20        # par ip, tous identifiants confondus
FENETRE_SECONDES = 300
_MAX_CLES = 10_000


def _purger(maintenant: float) -> None:
    if len(_echecs) < _MAX_CLES:
        return
    for k in list(_echecs):
        _echecs[k] = [t for t in _echecs[k] if maintenant - t < FENETRE_SECONDES]
        if not _echecs[k]:
            del _echecs[k]


def verifier_tentatives(cle: str, max_essais: int = MAX_ESSAIS) -> None:
    maintenant = time.time()
    with _verrou:
        _purger(maintenant)
        _echecs[cle] = [t for t in _echecs[cle] if maintenant - t < FENETRE_SECONDES]
        if len(_echecs[cle]) >= max_essais:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez dans quelques minutes.",
            )


def enregistrer_echec(cle: str) -> None:
    with _verrou:
        _echecs[cle].append(time.time())


def effacer_echecs(cle: str) -> None:
    with _verrou:
        _echecs.pop(cle, None)