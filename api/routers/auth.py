import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.deps import get_db
from api.rate_limit import verifier_tentatives, enregistrer_echec, effacer_echecs
from api.schemas import (
    LoginRequest, TokenResponse, VendeurLoginRequest, VendeurTokenResponse, VendeurProfile,
    AdminLoginRequest, AdminTokenResponse,
)
from api.security import (
    verify_password, create_access_token, create_vendeur_token, nouveau_sel_session,
    create_admin_token, empreinte_mot_de_passe,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


# 🛡️ 1. FONCTION DE RÉCUPÉRATION DE L'IP RÉELLE (DÉFINITION)
def get_real_client_ip(request: Request) -> str:
    """Extrait l'adresse IP réelle de la requête, même derrière Nginx / Cloudflare."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "inconnue"


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    # 🛡️ 2. REMPLACEMENT DANS LA ROUTE CLIENT (Ligne 21)
    ip = get_real_client_ip(request)
    cle = f"client:{ip}:{payload.code_client}"
    verifier_tentatives(cle)

    client = conn.execute(
        "SELECT * FROM clients WHERE code=?", (payload.code_client,)
    ).fetchone()

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
    Authentification des commerciaux (tournée Silwane Androway).
    """
    # 🛡️ 3. REMPLACEMENT DANS LA ROUTE VENDEUR (Ligne 65)
    ip = get_real_client_ip(request)
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
    cle = f"admin:{get_real_client_ip(request)}:{username}"
    verifier_tentatives(cle)

    user = rbac.authentifier(conn, username, payload.password)
    if user is None:
        enregistrer_echec(cle)
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
