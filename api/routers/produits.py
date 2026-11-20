import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.deps import get_current_client_or_vendeur, get_db
from api.schemas import ProduitCatalogue
from api.princing import resolve_prix

router = APIRouter(prefix="/produits", tags=["Catalogue Produits"])


@router.get("", response_model=list[ProduitCatalogue])
def get_catalogue(
    q: Optional[str] = Query(None, description="Recherche par désignation ou code"),
    client_id: Optional[int] = Query(
        None,
        description="ID du client pour les prix personnalisés (réservé aux commerciaux)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: dict = Depends(get_current_client_or_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Catalogue des produits avec calcul des tarifs personnalisés :
    1. CLIENT connecté : utilise exclusivement son propre client_id (refuse tout ?client_id= d'un tiers).
    2. VENDEUR connecté : peut spécifier ?client_id=X pour afficher le tarif du client visité.
    """
    if auth["type"] == "client":
        own_id = auth["client"]["id"]
        if client_id is not None and client_id != own_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé aux tarifs d'un autre client.",
            )
        target_client_id = own_id
    else:
        target_client_id = client_id

    # Requête de recherche (exclut les produits supprimés et désactivés)
    if q:
        q_esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{q_esc}%"
        query_str = """SELECT * FROM produits
                       WHERE (designation LIKE ? ESCAPE '\\' OR code LIKE ? ESCAPE '\\')
                         AND (supprime IS NULL OR supprime = 0)
                         AND (actif IS NULL OR actif = 1)
                       ORDER BY designation ASC LIMIT ? OFFSET ?"""
        rows = conn.execute(query_str, (pattern, pattern, limit, offset)).fetchall()
    else:
        query_str = """SELECT * FROM produits
                       WHERE (supprime IS NULL OR supprime = 0)
                         AND (actif IS NULL OR actif = 1)
                       ORDER BY designation ASC LIMIT ? OFFSET ?"""
        rows = conn.execute(query_str, (limit, offset)).fetchall()

    result = []
    for r in rows:
        p_id = r["id"]
        col_keys = r.keys()

        # Si on a un client cible (client connecté ou client sélectionné par le commercial)
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

        facteur = float(r["facteur_conversion"] if ("facteur_conversion" in col_keys and r["facteur_conversion"] is not None) else 1.0)
        if facteur <= 0:
            facteur = 1.0

        result.append(
            ProduitCatalogue(
                id=p_id,
                code=r["code"] or f"PRD-{p_id}",
                designation=r["designation"] or "",
                unite=r["unite"] if ("unite" in col_keys and r["unite"]) else "Pièce",
                facteur_conversion=facteur,
                prix_unitaire=prix_affiche,
                stock_actuel=stock,
                tva=tva,
            )
        )

    return result