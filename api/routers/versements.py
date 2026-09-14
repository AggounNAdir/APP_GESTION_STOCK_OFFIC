import sqlite3
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from api.deps import get_db, get_current_client
from api.schemas import VersementIn, Versement

router = APIRouter(prefix="/versements", tags=["Versements & Règlements"])

@router.get("", response_model=list[Versement])
def list_versements(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    rows = conn.execute(
        """SELECT * FROM versements WHERE client_id=?
           ORDER BY date_vers DESC, id DESC LIMIT ? OFFSET ?""",
        (client["id"], limit, offset),
    ).fetchall()

    return [
        Versement(
            id=r["id"],
            numero=r["numero"],
            date_vers=r["date_vers"],
            montant=float(r["montant"] or 0),
            mode=r["mode"],
            reference=r.get("reference")
        )
        for r in rows
    ]

@router.post("", response_model=Versement, status_code=status.HTTP_201_CREATED)
def create_versement(
    payload: VersementIn,
    conn: sqlite3.Connection = Depends(get_db),
):
    today = date.today().strftime("%Y%m%d")
    count = conn.execute("SELECT COUNT(*) FROM versements WHERE date_vers LIKE ?", (f"{date.today()}%",)).fetchone()[0]
    numero = f"RC-{today}-{count + 1:04d}"
    
    conn.execute(
        """INSERT INTO versements (numero, date_vers, client_id, vendeur_id, montant, mode, reference)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (numero, date.today().isoformat(), payload.client_id, payload.vendeur_id, payload.montant, payload.mode, payload.reference)
    )
    
    conn.execute(
        "UPDATE clients SET solde = MAX(0, solde - ?) WHERE id = ?",
        (payload.montant, payload.client_id)
    )
    
    new_solde = conn.execute("SELECT solde FROM clients WHERE id=?", (payload.client_id,)).fetchone()["solde"]
    conn.commit()
    
    return {"id": 0, "numero": numero, "date_vers": date.today().isoformat(), "montant": payload.montant, "mode": payload.mode, "reference": payload.reference, "nouveau_solde": new_solde}

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
