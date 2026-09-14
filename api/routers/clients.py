import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from api.deps import get_db, get_current_client
from api.schemas import ClientProfile, Facture, Versement, BonVente
from api.princing import resolve_prix

router = APIRouter(prefix="/clients", tags=["Client & Compte"])


@router.get("/me", response_model=ClientProfile)
def get_my_profile(
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retourne le profil détaillé du client connecté (solde, niveau de prix, etc.)."""
    niveau_row = conn.execute(
        "SELECT niveau FROM clients_niveau_prix WHERE client_id=?", (client["id"],)
    ).fetchone()
    niveau = niveau_row["niveau"] if niveau_row else "detail"

    return ClientProfile(
        id=client["id"],
        code=client["code"],
        nom=client["nom"],
        adresse=client["adresse"],
        tel=client["tel"],
        email=client["email"],
        solde=float(client["solde"] or 0.0),
        niveau_prix=niveau,
    )


@router.get("/me/ventes", response_model=list[BonVente])
def get_my_sales(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Historique des bons de vente (commandes validées/livrées) du client connecté."""
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
            {
                "produit_id": lr["produit_id"],
                "designation": lr["designation"] or "Article",
                "quantite": float(lr["quantite"]),
                "prix_unitaire": float(lr["prix_unitaire"]),
                "total": float(lr["total"]),
            }
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


@router.get("/me/factures", response_model=list[Facture])
def get_my_invoices(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Historique des factures du client connecté."""
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


@router.get("/me/versements", response_model=list[Versement])
def get_my_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Historique des versements / règlements effectués par le client."""
    rows = conn.execute(
        """SELECT * FROM versements_clients WHERE client_id=?
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
