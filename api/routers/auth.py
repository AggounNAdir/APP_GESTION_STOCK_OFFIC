import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.deps import get_db
from api.rate_limit import verifier_tentatives, enregistrer_echec, effacer_echecs
from api.schemas import LoginRequest, TokenResponse, VendeurLoginRequest, VendeurTokenResponse, VendeurProfile
from api.security import (
    verify_password, create_access_token, create_vendeur_token, nouveau_sel_session,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    ip = request.client.host if request.client else "inconnue"
    cle = f"client:{ip}:{payload.code_client}"
    verifier_tentatives(cle)

    client = conn.execute(
        "SELECT * FROM clients WHERE code=?", (payload.code_client,)
    ).fetchone()

    # Message volontairement identique en cas de code inconnu ou mot de passe
    # invalide, pour ne pas révéler quels codes clients existent.
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Code client ou mot de passe incorrect.",
    )

    if client is None:
        enregistrer_echec(cle)
        raise invalid

    if not verify_password(payload.password, client["password_hash"]):
        enregistrer_echec(cle)
        raise invalid

    if not (client["portail_actif"] or 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès au portail désactivé pour ce compte. Contactez votre fournisseur.",
        )

    effacer_echecs(cle)

    token = create_access_token(client["id"], client["code"])
    return TokenResponse(access_token=token)

@router.post("/login-vendeur", response_model=VendeurTokenResponse)
def login_vendeur(
    payload: VendeurLoginRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Authentification des commerciaux (tournée Silwane Androway). Jeton
    séparé de celui des clients — voir api/deps.get_current_vendeur.
    """
    ip = request.client.host if request.client else "inconnue"
    cle = f"vendeur:{ip}:{payload.code_vendeur}"
    verifier_tentatives(cle)

    vendeur = conn.execute(
        "SELECT * FROM vendeurs WHERE code=?", (payload.code_vendeur,)
    ).fetchone()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Code vendeur ou mot de passe incorrect.",
    )

    if vendeur is None:
        enregistrer_echec(cle)
        raise invalid

    if not verify_password(payload.password, vendeur["password_hash"] if "password_hash" in vendeur.keys() else None):
        enregistrer_echec(cle)
        raise invalid

    if not (vendeur["actif"] if "actif" in vendeur.keys() else 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès désactivé pour ce compte vendeur. Contactez votre administrateur.",
        )

    effacer_echecs(cle)

    # Sel de session : créé s'il est absent (premier login, ou après révocation).
    sel = vendeur["session_salt"]
    if not sel:
        sel = nouveau_sel_session()
        conn.execute("UPDATE vendeurs SET session_salt=? WHERE id=?", (sel, vendeur["id"]))
        conn.commit()

    token = create_vendeur_token(vendeur["id"], vendeur["code"], sel)
    return VendeurTokenResponse(
        access_token=token,
        vendeur=VendeurProfile(id=vendeur["id"], code=vendeur["code"], nom=vendeur["nom"], tel=vendeur["tel"]),
    )