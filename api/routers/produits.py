import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query
from api.deps import get_db, get_current_client
from api.schemas import ProduitCatalogue
from api.princing import resolve_prix

router = APIRouter(prefix="/produits", tags=["Catalogue Produits"])


@router.get("", response_model=list[ProduitCatalogue])
def get_catalogue(
    q: Optional[str] = Query(None, description="Recherche par désignation ou code"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Retourne le catalogue des produits actifs avec les prix personnalisés
    selon le niveau de prix ou le tarif spécial du client connecté.
    """
    client_id = client["id"]
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
        prix_perso = resolve_prix(conn, client_id, p_id)
        stock = float(r["stock_actuel"] if "stock_actuel" in r.keys() else 0.0)
        tva = float(r["tva"] if "tva" in r.keys() else 0.0)

        result.append(
            ProduitCatalogue(
                id=p_id,
                code=r["code"] or f"PRD-{p_id}",
                designation=r["designation"] or "",
                unite=r["unite"] if "unite" in r.keys() else "U",
                prix_unitaire=prix_perso,
                stock_actuel=stock,
                tva=tva,
            )
        )
    return result
