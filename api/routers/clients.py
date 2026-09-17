import sqlite3
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from api.deps import get_db, get_current_client
from api.schemas import ClientProfile, Facture, Versement, BonVente, ProspectIn, ProspectOut
from api.princing import resolve_prix

router = APIRouter(prefix="/clients", tags=["Client & Compte"])


@router.post("/prospect", response_model=ProspectOut, status_code=status.HTTP_201_CREATED)
def create_prospect(payload: ProspectIn, conn: sqlite3.Connection = Depends(get_db)):
    """
    Enregistre un prospect saisi sur le terrain (Silwane Androway).
    Un prospect n'est PAS un client : il n'a pas de compte, pas de solde,
    et n'apparaît pas dans la gestion des clients tant que le personnel ne
    l'a pas validé/converti explicitement depuis l'application bureau.

    ⚠️ Pas d'authentification (voir api/routers/tournee.py) : le portail
    n'a pas encore de login vendeur séparé du login client.
    """
    if not payload.nom.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom du prospect est obligatoire.",
        )

    code = payload.code
    if not code:
        today = date.today().strftime("%Y%m%d")
        count = conn.execute(
            "SELECT COUNT(*) FROM prospects_clients WHERE date_creation LIKE ?",
            (f"{date.today()}%",),
        ).fetchone()[0]
        code = f"PROSP-{today}-{count + 1:04d}"

    date_creation = datetime.now().isoformat(timespec="seconds")

    try:
        cursor = conn.execute(
            """INSERT INTO prospects_clients
               (code, nom, tel, adresse, wilaya, latitude, longitude, vendeur_id, date_creation, statut)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Nouveau')""",
            (
                code,
                payload.nom,
                payload.tel,
                payload.adresse,
                payload.wilaya,
                payload.resolved_lat(),
                payload.resolved_lng(),
                payload.vendeur_id,
                date_creation,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un prospect avec le code '{code}' existe déjà.",
        )

    return ProspectOut(
        id=cursor.lastrowid,
        code=code,
        nom=payload.nom,
        tel=payload.tel,
        adresse=payload.adresse,
        wilaya=payload.wilaya,
        latitude=payload.resolved_lat(),
        longitude=payload.resolved_lng(),
        date_creation=date_creation,
        statut="Nouveau",
    )


@router.get("/prospects", response_model=list[ProspectOut])
def list_prospects(
    statut: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste des prospects terrain — destinée à l'écran de validation côté application bureau."""
    query = "SELECT * FROM prospects_clients WHERE 1=1"
    params: list = []
    if statut:
        query += " AND statut=?"
        params.append(statut)
    query += " ORDER BY date_creation DESC, id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = conn.execute(query, params).fetchall()
    return [
        ProspectOut(
            id=r["id"],
            code=r["code"],
            nom=r["nom"],
            tel=r["tel"],
            adresse=r["adresse"],
            wilaya=r["wilaya"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            date_creation=r["date_creation"],
            statut=r["statut"],
        )
        for r in rows
    ]


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
@router.get("", response_model=list[ClientProfile])
def list_clients(
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste tous les clients avec leur solde officiel pour la tournée."""
    rows = conn.execute(
        "SELECT id, code, nom, adresse, tel, email, solde FROM clients ORDER BY nom ASC"
    ).fetchall()
    return [
        ClientProfile(
            id=r["id"],
            code=r["code"] if "code" in r.keys() and r["code"] else f"CLT-{r['id']:04d}",
            nom=r["nom"],
            adresse=r["adresse"] if "adresse" in r.keys() else None,
            tel=r["tel"] if "tel" in r.keys() else None,
            email=r["email"] if "email" in r.keys() else None,
            solde=float(r["solde"] or 0.0),
            niveau_prix="detail",
        )
        for r in rows
    ]
class ProspectCreateIn(BaseModel):
  nom: str
  tel: Optional[str] = None
  adresse: Optional[str] = None
  wilaya: Optional[str] = None
  code: Optional[str] = None
  solde_initial: Optional[float] = 0.0


@router.get("/prospects")
def list_prospects(
        vendeur_id: Optional[int] = Query(None),
        conn: sqlite3.Connection = Depends(get_db),
    ):
    """Retourne les prospects créés par les vendeurs Androway."""
    query = "SELECT * FROM prospects_vendeurs"
    params = []
    if vendeur_id:
        query += " WHERE vendeur_id = ?"
        params.append(vendeur_id)
    query += " ORDER BY id DESC"

    rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


@router.post("/prospect", status_code=status.HTTP_201_CREATED)
def create_prospect_terrain(
        payload: ProspectCreateIn,
        vendeur_id: Optional[int] = None,
        conn: sqlite3.Connection = Depends(get_db),
    ):
    """Enregistre un nouveau prospect créé par un commercial sur Androway."""
    today = date.today().isoformat()
    code = payload.code
    if not code:
        count = conn.execute("SELECT COUNT(*) FROM prospects_vendeurs").fetchone()[
            0
        ]
        code = f"PROSP-{(count + 1):03d}"

    cursor = conn.execute(
        """INSERT INTO prospects_vendeurs (code, nom, vendeur_id, tel, adresse, ville, solde, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            code,
            payload.nom,
            vendeur_id,
            payload.tel,
            payload.adresse,
            payload.wilaya,
            payload.solde_initial or 0.0,
            today,
        ),
    )
    conn.commit()
    return {"id": cursor.lastrowid, "code": code, "nom": payload.nom}