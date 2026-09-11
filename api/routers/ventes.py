import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from api.deps import get_db, get_current_client
from api.schemas import BonVente, LigneVente

router = APIRouter(prefix="/ventes", tags=["Ventes"])


@router.get("", response_model=list[BonVente])
def list_ventes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste tous les bons de vente du client connecté."""
    rows = conn.execute(
        """SELECT * FROM bons_vente WHERE client_id=?
           ORDER BY date_bon DESC, id DESC LIMIT ? OFFSET ?""",
        (client["id"], limit, offset),
    ).fetchall()

    result = []
    for r in rows:
        bv_id = r["id"]
        lignes_rows = conn.execute(
            """SELECT l.*, p.designation FROM lignes_vente l
               LEFT JOIN produits p ON l.produit_id = p.id
               WHERE l.bon_vente_id=?""",
            (bv_id,),
        ).fetchall()
        lignes = [
            LigneVente(
                produit_id=lr["produit_id"],
                designation=lr["designation"] or "Article",
                quantite=float(lr["quantite"]),
                prix_unitaire=float(lr["prix_unitaire"]),
                total=float(lr["total"]),
            )
            for lr in lignes_rows
        ]
        result.append(
            BonVente(
                id=bv_id,
                numero=r["numero"],
                date_bon=r["date_bon"],
                total=float(r["total"]),
                statut=r["statut"] if "statut" in r.keys() else "Validé",
                lignes=lignes,
            )
        )
    return result


@router.get("/{vente_id}", response_model=BonVente)
def get_vente_detail(
    vente_id: int,
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Détail d'un bon de vente spécifique du client."""
    r = conn.execute(
        "SELECT * FROM bons_vente WHERE id=? AND client_id=?",
        (vente_id, client["id"]),
    ).fetchone()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bon de vente introuvable.",
        )

    lignes_rows = conn.execute(
        """SELECT l.*, p.designation FROM lignes_vente l
           LEFT JOIN produits p ON l.produit_id = p.id
           WHERE l.bon_vente_id=?""",
        (vente_id,),
    ).fetchall()
    lignes = [
        LigneVente(
            produit_id=lr["produit_id"],
            designation=lr["designation"] or "Article",
            quantite=float(lr["quantite"]),
            prix_unitaire=float(lr["prix_unitaire"]),
            total=float(lr["total"]),
        )
        for lr in lignes_rows
    ]

    return BonVente(
        id=r["id"],
        numero=r["numero"],
        date_bon=r["date_bon"],
        total=float(r["total"]),
        statut=r["statut"] if "statut" in r.keys() else "Validé",
        lignes=lignes,
    )
