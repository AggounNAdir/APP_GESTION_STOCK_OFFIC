import ipaddress
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api import config
from api.deps import get_db
from api.rate_limit import (
    verifier_tentatives, enregistrer_echec, effacer_echecs, MAX_ESSAIS_IP,
)
from api.schemas import (
    LoginRequest, TokenResponse, VendeurLoginRequest, VendeurTokenResponse, VendeurProfile,
    AdminLoginRequest, AdminTokenResponse,
)
from api.security import (
    verify_password, create_access_token, create_vendeur_token, nouveau_sel_session,
    create_admin_token, empreinte_mot_de_passe,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _est_ip_valide(val: str) -> bool:
    try:
        ipaddress.ip_address(val)
        return True
    except ValueError:
        return False


def _est_proxy_de_confiance(host: str, trusted_proxies: tuple[str, ...]) -> bool:
    if not host or not trusted_proxies:
        return False
    if host in trusted_proxies:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    for entry in trusted_proxies:
        try:
            if "/" in entry:
                if ip in ipaddress.ip_network(entry, strict=False):
                    return True
            elif ip == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def get_real_client_ip(request: Request) -> str:
    """Extrait l'IP cliente sans faire confiance aux en-têtes forgés hors proxy autorisé."""
    peer_ip = request.client.host if request.client else "inconnue"
    trusted = config.TRUSTED_PROXIES
    if not _est_proxy_de_confiance(peer_ip, trusted):
        return peer_ip

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        for hop in reversed(hops):
            if _est_ip_valide(hop) and not _est_proxy_de_confiance(hop, trusted):
                return hop

    real_ip = (request.headers.get("X-Real-IP") or "").strip()
    if real_ip and _est_ip_valide(real_ip):
        return real_ip

    return peer_ip

def _verifier_limites(ip: str, prefixe: str, identifiant: str) -> tuple[str, str]:
    """Bloque si trop d'échecs pour ce couple ip+identifiant OU pour cette ip seule."""
    cle_id = f"{prefixe}:{ip}:{identifiant}"
    cle_ip = f"{prefixe}-ip:{ip}"
    verifier_tentatives(cle_ip, MAX_ESSAIS_IP)
    verifier_tentatives(cle_id)
    return cle_id, cle_ip


def _noter_echec(cle_id: str, cle_ip: str) -> None:
    enregistrer_echec(cle_id)
    enregistrer_echec(cle_ip)

@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    ip = get_real_client_ip(request)
    cle, cle_ip = _verifier_limites(ip, "client", payload.code_client)

    client = conn.execute(
        "SELECT * FROM clients WHERE code=?", (payload.code_client,)
    ).fetchone()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Code client ou mot de passe incorrect.",
    )

    if client is None:
        verify_password(payload.password, None)  # même durée qu'un vrai test bcrypt
        _noter_echec(cle, cle_ip)
        raise invalid

    if not verify_password(payload.password, client["password_hash"]):
        _noter_echec(cle, cle_ip)
        raise invalid

    if not (client["portail_actif"] or 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès au portail désactivé pour ce compte. Contactez votre fournisseur.",
        )

    effacer_echecs(cle)  # on ne remet PAS à zéro le compteur par IP

    token = create_access_token(
        client["id"], client["code"], empreinte_mot_de_passe(client["password_hash"])
    )
    return TokenResponse(access_token=token)


@router.post("/login-vendeur", response_model=VendeurTokenResponse)
def login_vendeur(
    payload: VendeurLoginRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Authentification des commerciaux (tournée Silwane Androway).
    """
    ip = get_real_client_ip(request)
    cle, cle_ip = _verifier_limites(ip, "vendeur", payload.code_vendeur)

    vendeur = conn.execute(
        "SELECT * FROM vendeurs WHERE code=?", (payload.code_vendeur,)
    ).fetchone()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Code vendeur ou mot de passe incorrect.",
    )

    if vendeur is None:
        verify_password(payload.password, None)
        _noter_echec(cle, cle_ip)
        raise invalid

    if not verify_password(payload.password, vendeur["password_hash"] if "password_hash" in vendeur.keys() else None):
        _noter_echec(cle, cle_ip)
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


@router.post("/login-admin", response_model=AdminTokenResponse)
def login_admin(
    payload: AdminLoginRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Connexion d'un utilisateur du bureau (table `utilisateurs`, mêmes comptes que
    l'application bureau). Tentatives limitées et tracées dans le journal d'audit.
    Un compte marqué « doit changer son mot de passe » (dont le compte admin/admin123
    créé à l'installation) est REFUSÉ : il faut d'abord le changer depuis le bureau.
    """
    from api import rbac

    username = (payload.username or "").strip()
    cle, cle_ip = _verifier_limites(get_real_client_ip(request), "admin", username)

    user = rbac.authentifier(conn, username, payload.password)
    if user is None:
        _noter_echec(cle, cle_ip)
        rbac.ajouter_audit(conn, "CONNEXION_ECHEC", utilisateur=username, reussite=False,
                           details="API : identifiant ou mot de passe incorrect")
        conn.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect.",
        )

    if user.get("doit_changer_mdp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Changez d'abord votre mot de passe depuis l'application bureau.",
        )

    effacer_echecs(cle)
    rbac.enregistrer_connexion(conn, user["id"])
    rbac.ajouter_audit(conn, "CONNEXION", utilisateur=user["nom_complet"], details="API")
    conn.commit()

    token = create_admin_token(user["id"], user["username"], empreinte_mot_de_passe(user["password_hash"]))
    return AdminTokenResponse(
        access_token=token, username=user["username"],
        nom_complet=user["nom_complet"], role=user["role"],
    )