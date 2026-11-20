"""
Sécurité : hachage des mots de passe (bcrypt) et jetons JWT.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import PyJWTError
import secrets
from api.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        # Même coût CPU qu'un vrai test, pour ne pas révéler qu'un compte n'existe pas.
        try:
            bcrypt.checkpw(password.encode("utf-8"), _DUMMY_HASH.encode("utf-8"))
        except ValueError:
            pass
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False

def create_access_token(client_id: int, code_client: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(client_id),
        "code": code_client,
        "exp": expire,
        "type": "client_portal",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "client_portal":
            return None
        return payload
    except PyJWTError:
        return None


def nouveau_sel_session() -> str:
    """Valeur aléatoire propre à une session vendeur (sert à révoquer les jetons)."""
    return secrets.token_hex(16)


def create_vendeur_token(vendeur_id: int, code_vendeur: str, session_salt: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(vendeur_id),
        "code": code_vendeur,
        "exp": expire,
        "type": "vendeur_portal",
        "sv": session_salt,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_vendeur_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "vendeur_portal":
            return None
        return payload
    except PyJWTError:
        return None


def empreinte_mot_de_passe(password_hash: str) -> str:
    """Empreinte courte du hash courant : un changement de mot de passe invalide les jetons admin."""
    import hashlib
    return hashlib.sha256((password_hash or "").encode("utf-8")).hexdigest()[:16]


def create_admin_token(user_id: int, username: str, empreinte_mdp: str) -> str:
    """Jeton d'un utilisateur du bureau (table `utilisateurs`). Le rôle n'y figure PAS :
    il est relu en base à chaque requête, donc un changement de rôle s'applique tout de suite."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "type": "admin_user",
        "pw": empreinte_mdp,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_admin_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "admin_user":
            return None
        return payload
    except PyJWTError:
        return None
