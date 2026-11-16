from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from datetime import date, datetime
from api.deps import get_current_vendeur, get_db, exiger_action, exiger_page
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
@router.post("/vendeurs/{vendeur_id}/versement", response_model=VersementVendeurAdminOut,
             status_code=status.HTTP_201_CREATED)
def admin_enregistrer_versement_vendeur(
    vendeur_id: int,
    payload: VersementVendeurAdminIn,
    user: dict = Depends(exiger_action("encaisser_versement_vendeur")),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Réservé aux utilisateurs du bureau autorisés à encaisser (admin, gestionnaire, caissier).
    Passe par le même service que l'application bureau (api/vendeur_dossier) : écrit dans
    `versements_vendeurs`, refuse un montant supérieur au reste à verser, et laisse une
    trace au journal d'audit.
    """
    if (payload.mode or "").strip().lower() not in ("espèces", "especes"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les remises en espèces sont enregistrées ici.",
        )
    if dossier.get_vendeur(conn, vendeur_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendeur introuvable.")
    try:
        res = dossier.creer_versement_admin(
            conn, vendeur_id, payload.montant,
            observations=payload.observations,
            cree_par=user["nom_complet"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return VersementVendeurAdminOut(
        id=res["id"], numero=res["numero"], date_vers=res["date_vers"],
        vendeur_id=vendeur_id, montant=res["montant"], mode="Espèces",
        observations=payload.observations,
    )

# 2. Obtenir le dossier complet de la Page Vendeur Admin :
@router.get("/vendeurs/{vendeur_id}/dossier")
def admin_obtenir_dossier_vendeur(
    vendeur_id: int,
    user: dict = Depends(exiger_page("vendeurs")),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Données complètes pour alimenter la Page Vendeur de l'Admin (utilisateur du bureau
    dont le rôle donne accès aux pages « équipe ») :
    - Situation globale (CA, Caisse en main, Total remis)
    - Liste des remises d'espèces à l'administration
    - État actuel du stock du camion
    """
    if dossier.get_vendeur(conn, vendeur_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendeur introuvable.")
    return {
        "situation": dossier.situation_vendeur(conn, vendeur_id),
        "remises_admin": dossier.versements_admin_vendeur(conn, vendeur_id),
        "stock_camion": dossier.stock_camion(conn, vendeur_id),
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
