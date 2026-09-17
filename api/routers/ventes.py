import sqlite3
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from api.deps import get_db, get_current_client, get_current_vendeur
from api.schemas import BonVente, LigneVente, SignatureBLIn, SignatureBLOut

router = APIRouter(prefix="/ventes", tags=["Ventes"])


@router.post("/bl/signature", response_model=SignatureBLOut, status_code=status.HTTP_201_CREATED)
def signer_bon_livraison(
    payload: SignatureBLIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Enregistre la signature électronique du client sur un bon de livraison
    (= un bon de vente). Déclenché par androwaySyncService (opération
    'signatureBL') une fois la tournée terrain synchronisée.

    Authentifié par le vendeur en tournée (voir api/deps.get_current_vendeur) :
    seul un commercial connecté peut faire signer un BL, pour éviter qu'un
    tiers non autorisé n'enregistre une fausse signature sur un bon existant.
    """
    if not payload.bon_vente_id and not payload.numero:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bon_vente_id ou numero requis pour identifier le bon de livraison.",
        )
    if not payload.signature or not payload.signature.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La signature (image encodée) est obligatoire.",
        )

    if payload.bon_vente_id:
        row = conn.execute(
            "SELECT id, numero FROM bons_vente WHERE id=?", (payload.bon_vente_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, numero FROM bons_vente WHERE numero=?", (payload.numero,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bon de livraison (bon de vente) introuvable.",
        )

    date_signature = datetime.now().isoformat(timespec="seconds")

    conn.execute(
        """UPDATE bons_vente
           SET signature_bl=?, signataire_nom=?, date_signature=?
           WHERE id=?""",
        (payload.signature, payload.signataire_nom, date_signature, row["id"]),
    )
    conn.commit()

    return SignatureBLOut(
        bon_vente_id=row["id"],
        numero=row["numero"],
        signataire_nom=payload.signataire_nom,
        date_signature=date_signature,
        statut="Signé",
    )


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
               WHERE l.bon_id=?""",
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
           WHERE l.bon_id=?""",
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