"""
Configuration de l'API Portail Client.
Toutes les valeurs sensibles peuvent être surchargées par des variables
d'environnement (recommandé en production).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ========== SÉCURITÉ / JWT ==========
# ⚠️ En production, définissez la variable d'environnement API_SECRET_KEY
# avec une valeur aléatoire longue (ex: python -c "import secrets;print(secrets.token_hex(32))")
SECRET_KEY = os.environ.get("API_SECRET_KEY", "dev-secret-key-CHANGEZ-MOI-en-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("API_TOKEN_EXPIRE_MINUTES", "60"))

if SECRET_KEY.startswith("dev-secret-key"):
    import warnings
    warnings.warn(
        "⚠️ API_SECRET_KEY n'est pas configurée : une clé de développement est utilisée. "
        "Définissez la variable d'environnement API_SECRET_KEY avant de déployer en production.",
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