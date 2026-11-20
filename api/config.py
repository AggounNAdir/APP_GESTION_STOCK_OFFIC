"""
Configuration de l'API Portail Client.
"""
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEV_SECRET_FILE = _PROJECT_ROOT / ".dev_secret_key"

# ========== SÉCURITÉ / JWT ==========
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("API_TOKEN_EXPIRE_MINUTES", "60"))


def _resoudre_secret_key(cle_path: Path = _DEV_SECRET_FILE) -> str:
    env_key = os.environ.get("API_SECRET_KEY", "").strip()
    if env_key:
        return env_key

    if os.environ.get("API_ENV", "").strip().lower() == "production":
        raise RuntimeError(
            "API_SECRET_KEY est obligatoire quand API_ENV=production. "
            "Générez-la avec : python -c \"import secrets;print(secrets.token_hex(32))\""
        )

    try:
        if cle_path.exists():
            saved = cle_path.read_text(encoding="utf-8").strip()
            if saved:
                return saved
        new_key = secrets.token_urlsafe(32)
        cle_path.write_text(new_key, encoding="utf-8")
        return new_key
    except OSError:
        return secrets.token_urlsafe(32)


SECRET_KEY = _resoudre_secret_key()

# ========== CORS DYNAMIQUE ==========
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _resoudre_cors_origins(origins_env: str | None = None) -> list[str]:
    raw = os.environ.get("API_CORS_ORIGINS", "") if origins_env is None else origins_env
    if os.environ.get("API_ENV", "").strip().lower() == "production" and not raw.strip():
        raise RuntimeError(
            "API_CORS_ORIGINS est obligatoire quand API_ENV=production pour sécuriser l'API !"
        )
    parsed = list(dict.fromkeys(o.strip() for o in raw.split(",") if o.strip()))
    return parsed or list(_DEFAULT_CORS_ORIGINS)


CORS_ORIGINS = _resoudre_cors_origins()

# ========== PROXIES DE CONFIANCE ==========
_trusted_proxies_env = os.environ.get("API_TRUSTED_PROXIES", "")
TRUSTED_PROXIES = tuple(
    p.strip() for p in _trusted_proxies_env.split(",") if p.strip()
)

# ========== PAGINATION ==========
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100