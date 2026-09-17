"""
Dépendances FastAPI communes : connexion DB par requête, client courant authentifié.
"""
import sqlite3
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from api.db import get_conn
from api.security import decode_access_token, decode_vendeur_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_vendeur = OAuth2PasswordBearer(tokenUrl="/auth/login-vendeur", auto_error=False)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def get_current_client(
    token: str = Depends(oauth2_scheme),
    conn: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée, veuillez vous reconnecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    client_id = payload.get("sub")
    if client_id is None:
        raise credentials_error

    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if client is None:
        raise credentials_error

    if not (client["portail_actif"] or 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès au portail désactivé pour ce compte. Contactez votre fournisseur.",
        )

    return client


def get_current_vendeur(
    token: str | None = Depends(oauth2_scheme_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row:
    """
    Authentifie le commercial/vendeur en tournée (Silwane Androway). Jeton
    JWT distinct de celui des clients (voir api/security.create_vendeur_token) :
    un token client ne peut pas passer ici, et réciproquement.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session vendeur invalide ou expirée, veuillez vous reconnecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    payload = decode_vendeur_token(token)
    if payload is None:
        raise credentials_error

    vendeur_id = payload.get("sub")
    if vendeur_id is None:
        raise credentials_error

    vendeur = conn.execute("SELECT * FROM vendeurs WHERE id=?", (vendeur_id,)).fetchone()
    if vendeur is None:
        raise credentials_error

    if not (vendeur["actif"] if "actif" in vendeur.keys() else 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès désactivé pour ce compte vendeur. Contactez votre administrateur.",
        )

    return vendeur
def get_current_client_or_vendeur(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """
    Accepte SOIT un jeton client SOIT un jeton vendeur.
    Permet à un client de passer sa propre commande,
    OU à un commercial en tournée de passer une commande pour un client.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée, veuillez vous reconnecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Tentative avec token CLIENT
    client_payload = decode_access_token(token)
    if client_payload and client_payload.get("sub"):
        client = conn.execute("SELECT * FROM clients WHERE id=?", (client_payload["sub"],)).fetchone()
        if client:
            return {"type": "client", "client": client, "vendeur": None}

    # 2. Tentative avec token VENDEUR (Androway)
    vendeur_payload = decode_vendeur_token(token)
    if vendeur_payload and vendeur_payload.get("sub"):
        vendeur = conn.execute("SELECT * FROM vendeurs WHERE id=?", (vendeur_payload["sub"],)).fetchone()
        if vendeur:
            return {"type": "vendeur", "client": None, "vendeur": vendeur}

    # Si aucun des deux n'est valide
    raise credentials_error