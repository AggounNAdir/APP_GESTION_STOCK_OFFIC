from fastapi import APIRouter, Depends
import sqlite3
from datetime import date
from api.deps import get_db

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get("/vendeurs")
def list_vendeurs(conn: sqlite3.Connection = Depends(get_db)):
    return [dict(r) for r in conn.execute("SELECT * FROM vendeurs WHERE actif=1").fetchall()]

@router.get("/ventes-vendeurs")
def get_ventes_vendeurs(vendeur_id: int = None, date_jour: str = None, conn: sqlite3.Connection = Depends(get_db)):
    query = """
        SELECT b.id, b.numero, b.date_bon, v.nom as nom_vendeur, c.code as code_client, c.nom as nom_client, c.tel, 
               b.total as montant_total, b.montant_verse, (b.total - b.montant_verse) as credit_genere, c.solde as solde_actuel
        FROM bons_vente b
        JOIN vendeurs v ON b.vendeur_id = v.id
        JOIN clients c ON b.client_id = c.id
        WHERE 1=1
    """
    params = []
    if vendeur_id:
        query += " AND b.vendeur_id = ?"
        params.append(vendeur_id)
    if date_jour:
        query += " AND b.date_bon = ?"
        params.append(date_jour)
    return [dict(r) for r in conn.execute(query, params).fetchall()]

@router.get("/situation-journaliere-vendeurs")
def get_situation_journaliere(date_jour: str = None, conn: sqlite3.Connection = Depends(get_db)):
    query = """
        SELECT v.nom, COUNT(b.id) as nb_ventes, SUM(b.total) as ca_total, SUM(b.montant_verse) as total_encaisse, SUM(b.total - b.montant_verse) as reste_credit
        FROM vendeurs v
        LEFT JOIN bons_vente b ON v.id = b.vendeur_id AND b.date_bon = ?
        GROUP BY v.id
    """
    return [dict(r) for r in conn.execute(query, (date_jour or date.today().isoformat(),)).fetchall()]

