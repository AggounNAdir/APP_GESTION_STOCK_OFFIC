from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from datetime import date, datetime
from api.deps import get_current_vendeur, get_db
from api.schemas import VersementVendeurAdminIn, VersementVendeurAdminOut
import api.vendeur_dossier as dossier
router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get("/vendeurs")
def list_vendeurs(
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT id, code, nom, tel FROM vendeurs WHERE id=? AND actif=1",
        (vendeur["id"],),
    ).fetchone()
    return [dict(row)] if row else []
# 1. Encaisser une remise d'espèces soumise par un vendeur :
@router.post("/vendeurs/{vendeur_id}/versement", response_model=VersementVendeurAdminOut)
def admin_enregistrer_versement_vendeur(
    vendeur_id: int,
    payload: VersementVendeurAdminIn,
    vendeur_auth: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Permet à l'Admin de valider la réception d'espèces remise par un vendeur et de lui délivrer son reçu de décharge.
    """
    today_str = date.today().strftime("%Y%m%d")
    count = conn.execute(
        "SELECT COUNT(*) FROM versements_vendeurs_admin WHERE date_vers LIKE ?",
        (f"{date.today()}%",)
    ).fetchone()[0]
    numero = f"VVA-{today_str}-{count + 1:04d}"
    date_vers = datetime.now().isoformat(timespec="seconds")

    cursor = conn.execute(
        """INSERT INTO versements_vendeurs_admin (numero, date_vers, vendeur_id, montant, mode, observations, date_creation)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (numero, date_vers, vendeur_id, payload.montant, payload.mode, payload.observations, date_vers)
    )
    conn.commit()

    return VersementVendeurAdminOut(
        id=cursor.lastrowid,
        numero=numero,
        date_vers=date_vers,
        vendeur_id=vendeur_id,
        montant=payload.montant,
        mode=payload.mode,
        observations=payload.observations,
    )

# 2. Obtenir le dossier complet de la Page Vendeur Admin :
@router.get("/vendeurs/{vendeur_id}/dossier")
def admin_obtenir_dossier_vendeur(
    vendeur_id: int,
    vendeur_auth: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Données complètes pour alimenter la Page Vendeur de l'Admin :
    - Situation globale (CA, Caisse en main, Total remis)
    - Liste des reçus de décharge d'espèces
    - État actuel du stock du camion
    """
    sit = dossier.situation_vendeur(conn, vendeur_id)
    remises = dossier.remises_vendeur_admin(conn, vendeur_id)
    camion = dossier.stock_camion(conn, vendeur_id)
    return {
        "situation": sit,
        "remises_admin": remises,
        "stock_camion": camion,
    }

@router.get("/ventes-vendeurs")
def get_ventes_vendeurs(
    vendeur_id: int = None,
    date_jour: str = None,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    if vendeur_id is not None and vendeur_id != vendeur["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez consulter que vos propres ventes.",
        )
    query = """
        SELECT b.id, b.numero, b.date_bon, v.nom as nom_vendeur,
               COALESCE(p.code, c.code) as code_client,
               COALESCE(p.nom, c.nom) as nom_client, c.tel,
               b.total as montant_total, b.montant_verse,
               (b.total - b.montant_verse) as credit_genere,
               COALESCE(p.solde, c.solde) as solde_actuel
        FROM bons_vente b
        JOIN vendeurs v ON b.vendeur_id = v.id
        JOIN clients c ON b.client_id = c.id
        LEFT JOIN prospects_clients p ON p.id = b.prospect_id
        WHERE b.vendeur_id = ?
    """
    params = [vendeur["id"]]
    if date_jour:
        query += " AND b.date_bon = ?"
        params.append(date_jour)
    return [dict(r) for r in conn.execute(query, params).fetchall()]

@router.get("/situation-journaliere-vendeurs")
def get_situation_journaliere(
    date_jour: str = None,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = """
        SELECT v.nom, COUNT(b.id) as nb_ventes, SUM(b.total) as ca_total, SUM(b.montant_verse) as total_encaisse, SUM(b.total - b.montant_verse) as reste_credit
        FROM vendeurs v
        LEFT JOIN bons_vente b ON v.id = b.vendeur_id AND b.date_bon = ?
        WHERE v.id = ?
        GROUP BY v.id
    """
    return [
        dict(r)
        for r in conn.execute(
            query, (date_jour or date.today().isoformat(), vendeur["id"])
        ).fetchall()
    ]
