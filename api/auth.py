import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_db
from api.schemas import LoginRequest, TokenResponse
from api.security import verify_password, create_access_token

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