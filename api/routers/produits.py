import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, Header
from api.deps import get_db
from api.schemas import ProduitCatalogue
from api.princing import resolve_prix
from api.security import decode_access_token

router = APIRouter(prefix="/produits", tags=["Catalogue Produits"])


@router.get("", response_model=list[ProduitCatalogue])
def get_catalogue(
    q: Optional[str] = Query(None, description="Recherche par désignation ou code"),
    client_id: Optional[int] = Query(None, description="ID du client pour les prix personnalisés (utile pour les vendeurs)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Catalogue des produits avec calcul des tarifs personnalisés :
    1. Si un CLIENT est connecté : utilise son jeton pour résoudre son prix personnalisé.
    2. Si un VENDEUR spécifie ?client_id=X : utilise ce client pour calculer le prix.
    3. Sinon : affiche le prix de vente standard (prix_vente ou prix_detail).
    """
    target_client_id = client_id

    # Si pas de client_id explicite, on extrait l'identifiant du client depuis le JWT
    if not target_client_id and authorization:
        token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            try:
                target_client_id = int(payload["sub"])
            except (ValueError, TypeError):
                pass

    # Requête de recherche
    if q:
        query_str = """SELECT * FROM produits
                       WHERE (designation LIKE ? OR code LIKE ?)
                         AND (supprime IS NULL OR supprime = 0)
                       ORDER BY designation ASC LIMIT ? OFFSET ?"""
        pattern = f"%{q}%"
        rows = conn.execute(query_str, (pattern, pattern, limit, offset)).fetchall()
    else:
        query_str = """SELECT * FROM produits
                       WHERE (supprime IS NULL OR supprime = 0)
                       ORDER BY designation ASC LIMIT ? OFFSET ?"""
        rows = conn.execute(query_str, (limit, offset)).fetchall()

    result = []
    for r in rows:
        p_id = r["id"]
        col_keys = r.keys()

        # Si on a un client cible (soit le client connecté, soit choisi par le commercial)
        if target_client_id:
            prix_affiche = resolve_prix(conn, target_client_id, p_id)
        else:
            # Tarif standard de la fiche produit
            if "prix_vente" in col_keys and r["prix_vente"] is not None:
                prix_affiche = float(r["prix_vente"])
            elif "prix_detail" in col_keys and r["prix_detail"] is not None:
                prix_affiche = float(r["prix_detail"])
            else:
                prix_affiche = 0.0

        stock = float(r["stock_actuel"] if ("stock_actuel" in col_keys and r["stock_actuel"] is not None) else 0.0)
        tva = float(r["tva"] if ("tva" in col_keys and r["tva"] is not None) else 0.0)

        # Récupération du facteur de conversion depuis la table SQLite
        facteur = float(r["facteur_conversion"] if ("facteur_conversion" in col_keys and r["facteur_conversion"] is not None) else 1.0)
        if facteur <= 0:
            facteur = 1.0

        result.append(
            ProduitCatalogue(
                id=p_id,
                code=r["code"] or f"PRD-{p_id}",
                designation=r["designation"] or "",
                unite=r["unite"] if ("unite" in col_keys and r["unite"]) else "Pièce",
                facteur_conversion=facteur,  # <--- TRANSMETTRE ICI
                prix_unitaire=prix_affiche,
                stock_actuel=stock,
                tva=tva,
            )
        )

    return result