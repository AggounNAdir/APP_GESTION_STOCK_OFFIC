"""
Router Tournée terrain — Silwane Androway.

Authentifié par le vendeur en tournée (voir api/deps.get_current_vendeur) :
le vendeur_id enregistré sur chaque pointage vient du jeton, jamais du
payload envoyé par le mobile, pour empêcher un vendeur de faire passer un
pointage sous l'identité d'un collègue.
"""
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status

from api.deps import get_db, get_current_vendeur
from api.schemas import PointageGpsIn, PointageOut

router = APIRouter(prefix="/tournee", tags=["Tournée Terrain (Androway)"])


def _enregistrer_pointage(
    conn: sqlite3.Connection, payload: PointageGpsIn, vendeur: sqlite3.Row
) -> PointageOut:
    data = payload.resolved()

    if data["client_id"] is None and not data["code_client"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id (ou clientId) requis pour enregistrer un pointage.",
        )

    # Si on a un client_id, on va chercher son code/nom réels pour ne pas
    # dépendre uniquement de ce que le mobile a mis en cache localement.
    code_client = data["code_client"]
    nom_client = data["nom_client"]
    if data["client_id"] is not None:
        row = conn.execute(
            "SELECT code, nom FROM clients WHERE id=?", (data["client_id"],)
        ).fetchone()
        if row is not None:
            code_client = row["code"]
            nom_client = row["nom"]

    date_pointage = data["date_pointage"] or datetime.now().isoformat(timespec="seconds")

    cursor = conn.execute(
        """INSERT INTO tournee_pointages
           (client_id, vendeur_id, code_client, nom_client, latitude, longitude, date_pointage, observations)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["client_id"],
            vendeur["id"],
            code_client,
            nom_client,
            data["latitude"],
            data["longitude"],
            date_pointage,
            data["observations"],
        ),
    )
    conn.commit()

    return PointageOut(
        id=cursor.lastrowid,
        client_id=data["client_id"],
        code_client=code_client,
        nom_client=nom_client,
        latitude=data["latitude"],
        longitude=data["longitude"],
        date_pointage=date_pointage,
        observations=data["observations"],
    )


@router.post("/pointage-gps", response_model=PointageOut, status_code=status.HTTP_201_CREATED)
def pointage_gps(
    payload: PointageGpsIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Appelé directement par gpsTourneeService.pointerPresenceVisite() : valide
    la présence du commercial chez le client avec preuve GPS immédiate.
    """
    return _enregistrer_pointage(conn, payload, vendeur)


@router.post("/pointage", response_model=PointageOut, status_code=status.HTTP_201_CREATED)
def pointage_offline(
    payload: PointageGpsIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Appelé via la file de synchronisation offline-first (androwaySyncService,
    opération de type 'pointageVisite') lorsque le mobile revient en ligne.
    Même logique métier que /pointage-gps ; endpoint séparé car c'est deux
    déclencheurs distincts côté portail.
    """
    return _enregistrer_pointage(conn, payload, vendeur)


@router.get("/pointages", response_model=list[PointageOut])
def list_pointages(
    client_id: Optional[int] = None,
    vendeur_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Liste des pointages terrain — destinée à un écran de supervision côté
    application bureau (suivi des tournées commerciales).
    """
    query = "SELECT * FROM tournee_pointages WHERE 1=1"
    params: list = []
    if client_id is not None:
        query += " AND client_id=?"
        params.append(client_id)
    if vendeur_id is not None:
        query += " AND vendeur_id=?"
        params.append(vendeur_id)
    query += " ORDER BY date_pointage DESC, id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = conn.execute(query, params).fetchall()
    return [
        PointageOut(
            id=r["id"],
            client_id=r["client_id"],
            code_client=r["code_client"],
            nom_client=r["nom_client"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            date_pointage=r["date_pointage"],
            observations=r["observations"],
        )
        for r in rows
    ]