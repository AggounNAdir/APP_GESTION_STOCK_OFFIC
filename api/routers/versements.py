import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from api.deps import get_db, get_current_client
from api.schemas import Versement

router = APIRouter(prefix="/versements", tags=["Versements & Règlements"])


@router.get("", response_model=list[Versement])
def list_versements(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste tous les versements et règlements effectués par le client."""
    rows = conn.execute(
        """SELECT * FROM versements WHERE client_id=?
           ORDER BY date_vers DESC, id DESC LIMIT ? OFFSET ?""",
        (client["id"], limit, offset),
    ).fetchall()

    return [
        Versement(
            id=r["id"],
            numero=r["numero"] if "numero" in r.keys() else f"VERS-{r['id']}",
            date_vers=r["date_vers"],
            montant=float(r["montant"] or 0),
            mode=r["mode"] if "mode" in r.keys() else "Espèces",
            reference=r["reference"] if "reference" in r.keys() else None,
        )
        for r in rows
    ]
