"""
Dépendances FastAPI communes : connexion DB par requête, client courant authentifié.
"""
import sqlite3
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from api.db import get_conn
from api.security import (
    decode_access_token, decode_vendeur_token, decode_admin_token, empreinte_mot_de_passe,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_vendeur = OAuth2PasswordBearer(tokenUrl="/auth/login-vendeur", auto_error=False)
oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="/auth/login-admin", auto_error=False)


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
    if payload.get("pw") != empreinte_mot_de_passe(client["password_hash"]):
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
        # Révocation : le sel du jeton doit correspondre à celui enregistré en base.
        
    sel_jeton = payload.get("sv")
    sel_base = vendeur["session_salt"] if "session_salt" in vendeur.keys() else None
    if not sel_jeton or not sel_base or sel_jeton != sel_base:
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
            if client_payload.get("pw") != empreinte_mot_de_passe(client["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session invalide ou expirée, veuillez vous reconnecter.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not (client["portail_actif"] or 0):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès au portail désactivé pour ce compte. Contactez votre fournisseur.",
                )
            return {"type": "client", "client": client, "vendeur": None}

    # 2. Tentative avec token VENDEUR (Androway)
    vendeur_payload = decode_vendeur_token(token)
    if vendeur_payload and vendeur_payload.get("sub"):
        vendeur = conn.execute("SELECT * FROM vendeurs WHERE id=?", (vendeur_payload["sub"],)).fetchone()
        if vendeur:
            sel_jeton = vendeur_payload.get("sv")
            sel_base = vendeur["session_salt"] if "session_salt" in vendeur.keys() else None
            if not sel_jeton or not sel_base or sel_jeton != sel_base:
                raise credentials_error
            if not (vendeur["actif"] if "actif" in vendeur.keys() else 1):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès désactivé pour ce compte vendeur. Contactez votre administrateur.",
                )
            return {"type": "vendeur", "client": None, "vendeur": vendeur}

    # Si aucun des deux n'est valide
    raise credentials_error


# ───────────────────── Utilisateurs du bureau (administration) ─────────────────────

def get_current_admin_user(
    token: str | None = Depends(oauth2_scheme_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """
    Authentifie un utilisateur du bureau (table `utilisateurs`) par un jeton de type
    `admin_user`, délivré uniquement par POST /auth/login-admin. Un jeton client ou
    vendeur n'est jamais accepté ici, et réciproquement. Le compte et son rôle sont
    relus en base à chaque requête : compte désactivé, mot de passe changé ou rôle
    modifié = effet immédiat.
    """
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session administrateur invalide ou expirée, veuillez vous reconnecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise erreur
    payload = decode_admin_token(token)
    if payload is None or payload.get("sub") is None:
        raise erreur
    row = conn.execute("SELECT * FROM utilisateurs WHERE id=?", (payload["sub"],)).fetchone()
    if row is None or not row["actif"]:
        raise erreur
    if payload.get("pw") != empreinte_mot_de_passe(row["password_hash"]):
        raise erreur
    if row["doit_changer_mdp"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mot de passe à changer depuis l'application bureau avant d'utiliser l'API.",
        )
    return dict(row)


def exiger_action(action_cle: str):
    """Dépendance : utilisateur du bureau autorisé pour cette ACTION sensible (api/rbac.ACTIONS)."""
    from api import rbac

    def _dep(user: dict = Depends(get_current_admin_user)) -> dict:
        if not rbac.peut(user["role"], action_cle):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Votre rôle ne permet pas cette opération.",
            )
        return user

    return _dep


def exiger_page(page_key: str):
    """Dépendance : utilisateur du bureau dont le rôle donne accès à cette page du menu."""
    from api import rbac

    def _dep(user: dict = Depends(get_current_admin_user)) -> dict:
        if not rbac.peut_voir_page(user["role"], page_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Votre rôle ne donne pas accès à cette information.",
            )
        return user

    return _dep
