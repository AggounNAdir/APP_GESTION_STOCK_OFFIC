import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from api.deps import get_db, get_current_client
from api.schemas import Facture

router = APIRouter(prefix="/factures", tags=["Factures"])


@router.get("", response_model=list[Facture])
def list_factures(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste toutes les factures du client connecté."""
    rows = conn.execute(
        """SELECT * FROM factures WHERE client_id=?
           ORDER BY date_facture DESC, id DESC LIMIT ? OFFSET ?""",
        (client["id"], limit, offset),
    ).fetchall()

    return [
        Facture(
            id=r["id"],
            numero=r["numero"],
            date_facture=r["date_facture"],
            total_ht=float(r["total_ht"] or 0),
            tva=float(r["tva"] or 0),
            total_ttc=float(r["total_ttc"] or 0),
            statut=r["statut"] if "statut" in r.keys() else "Émise",
            date_echeance=r["date_echeance"] if "date_echeance" in r.keys() else None,
        )
        for r in rows
    ]


@router.get("/{facture_id}", response_model=Facture)
def get_facture_detail(
    facture_id: int,
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Détail d'une facture spécifique du client."""
    r = conn.execute(
        "SELECT * FROM factures WHERE id=? AND client_id=?",
        (facture_id, client["id"]),
    ).fetchone()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture introuvable.",
        )

    return Facture(
        id=r["id"],
        numero=r["numero"],
        date_facture=r["date_facture"],
        total_ht=float(r["total_ht"] or 0),
        tva=float(r["tva"] or 0),
        total_ttc=float(r["total_ttc"] or 0),
        statut=r["statut"] if "statut" in r.keys() else "Émise",
        date_echeance=r["date_echeance"] if "date_echeance" in r.keys() else None,
    )
