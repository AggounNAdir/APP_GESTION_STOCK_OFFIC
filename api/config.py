"""
Configuration de l'API Portail Client.
"""
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# ========== SÉCURITÉ / JWT ==========
SECRET_KEY = os.environ.get("API_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("API_TOKEN_EXPIRE_MINUTES", "60"))

if not SECRET_KEY:
    if os.environ.get("API_ENV", "").lower() == "production":
        raise RuntimeError(
            "API_SECRET_KEY est obligatoire quand API_ENV=production. "
            "Générez-la avec : python -c \"import secrets;print(secrets.token_hex(32))\""
        )
    SECRET_KEY = secrets.token_urlsafe(32)

# ========== CORS DYNAMIQUE ==========
_origins_env = os.environ.get("API_CORS_ORIGINS", "")

# Bloque le serveur en prod si la variable est absente
if os.environ.get("API_ENV", "").lower() == "production" and not _origins_env:
    raise RuntimeError(
        "API_CORS_ORIGINS est obligatoire quand API_ENV=production pour sécuriser l'API !"
    )

CORS_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# ========== PAGINATION ==========
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100