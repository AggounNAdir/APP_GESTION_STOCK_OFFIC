"""
Configuration de l'API Portail Client.
Toutes les valeurs sensibles peuvent être surchargées par des variables
d'environnement (recommandé en production).
"""
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# ========== SÉCURITÉ / JWT ==========
# En production, API_SECRET_KEY doit contenir une valeur aléatoire longue
# (ex: python -c "import secrets;print(secrets.token_hex(32))").
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
    import warnings
    warnings.warn(
        "API_SECRET_KEY n'est pas configurée : une clé aléatoire temporaire est utilisée. "
        "Configurez-la pour préserver les sessions entre redémarrages.",
        stacklevel=2,
    )

# ========== CORS ==========
# Liste des origines autorisées à consommer l'API (le domaine du portail client).
# Surchargeable via API_CORS_ORIGINS="https://portail.exemple.com,https://autre.exemple.com"
_origins_env = os.environ.get("API_CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]

# ========== PAGINATION ==========
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100