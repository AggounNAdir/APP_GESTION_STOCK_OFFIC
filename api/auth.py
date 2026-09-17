import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_db
from api.schemas import LoginRequest, TokenResponse, VendeurLoginRequest, VendeurTokenResponse, VendeurProfile
from api.security import verify_password, create_access_token, create_vendeur_token

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
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
        raise invalid

    if not verify_password(payload.password, client["password_hash"]):
        raise invalid

    if not (client["portail_actif"] or 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès au portail désactivé pour ce compte. Contactez votre fournisseur.",
        )

    token = create_access_token(client["id"], client["code"])
    return TokenResponse(access_token=token)


@router.post("/login-vendeur", response_model=VendeurTokenResponse)
def login_vendeur(payload: VendeurLoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    """
    Authentification des commerciaux (tournée Silwane Androway). Jeton
    séparé de celui des clients — voir api/deps.get_current_vendeur.
    """
    vendeur = conn.execute(
        "SELECT * FROM vendeurs WHERE code=?", (payload.code_vendeur,)
    ).fetchone()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Code vendeur ou mot de passe incorrect.",
    )

    if vendeur is None:
        raise invalid

    if not verify_password(payload.password, vendeur["password_hash"] if "password_hash" in vendeur.keys() else None):
        raise invalid

    if not (vendeur["actif"] if "actif" in vendeur.keys() else 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès désactivé pour ce compte vendeur. Contactez votre administrateur.",
        )

    token = create_vendeur_token(vendeur["id"], vendeur["code"])
    return VendeurTokenResponse(
        access_token=token,
        vendeur=VendeurProfile(id=vendeur["id"], code=vendeur["code"], nom=vendeur["nom"], tel=vendeur["tel"]),
    )