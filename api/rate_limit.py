"""Limiteur de tentatives de connexion (en mémoire, par clé ip:code)."""
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, status

_echecs = defaultdict(list)
_verrou = threading.Lock()

MAX_ESSAIS = 5
FENETRE_SECONDES = 300


def verifier_tentatives(cle: str) -> None:
    maintenant = time.time()
    with _verrou:
        _echecs[cle] = [t for t in _echecs[cle] if maintenant - t < FENETRE_SECONDES]
        if len(_echecs[cle]) >= MAX_ESSAIS:
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