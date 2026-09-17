import sqlite3
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.deps import get_current_client_or_vendeur, get_db, get_current_client
from api.schemas import CommandeIn, CommandeOut, LigneCommandeOut
from api.princing import resolve_prix

router = APIRouter(prefix="/commandes", tags=["Commandes Portail"])

@router.post("", response_model=CommandeOut, status_code=status.HTTP_201_CREATED)
def create_commande(
    payload: CommandeIn,
    auth: dict = Depends(get_current_client_or_vendeur),  # <-- Remplace get_current_client
    conn: sqlite3.Connection = Depends(get_db),
):
    # Si c'est un client connecté :
    if auth["type"] == "client":
        client_id = auth["client"]["id"]
        vendeur_id = payload.vendeur_id or (auth["client"]["vendeur_id"] if "vendeur_id" in auth["client"].keys() else None)
    
    # Si c'est un commercial en tournée Androway :
    else:
        # Le vendeur doit obligatoirement cibler un client via payload.client_id
        client_id = payload.client_id
        vendeur_id = auth["vendeur"]["id"]

        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Veuillez spécifier le client_id pour lequel vous passez cette commande.",
            )

    today = date.today().isoformat()
    num_date = date.today().strftime("%Y%m%d")
    
    count_today = conn.execute(
        "SELECT COUNT(*) FROM commandes_clients WHERE date_commande LIKE ?",
        (f"{date.today()}%",)
    ).fetchone()[0]
    numero = f"CMD-{num_date}-{count_today + 1:04d}"

    total_estime = 0.0
    lignes_data = []

    for item in payload.lignes:
        produit = conn.execute(
            "SELECT * FROM produits WHERE id=? AND (supprime IS NULL OR supprime = 0)",
            (item.produit_id,)
        ).fetchone()
        if not produit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produit ID {item.produit_id} introuvable.",
            )

        prix_unit = resolve_prix(conn, client_id, item.produit_id)
        total_ligne = float(item.quantite) * prix_unit
        total_estime += total_ligne

        lignes_data.append({
            "produit_id": item.produit_id,
            "designation": produit["designation"],
            "quantite": float(item.quantite),
            "prix_unitaire_estime": prix_unit,
            "total_estime": total_ligne,
        })

    cursor = conn.execute(
        """INSERT INTO commandes_clients 
           (numero, client_id, vendeur_id, date_commande, statut, total_estime, observations)
           VALUES (?, ?, ?, ?, 'En attente', ?, ?)""",
        (numero, client_id, vendeur_id, today, total_estime, payload.observations)
    )
    commande_id = cursor.lastrowid

    for ld in lignes_data:
        conn.execute(
            """INSERT INTO lignes_commande_client 
               (commande_id, produit_id, quantite, prix_unitaire_estime, total_estime)
               VALUES (?, ?, ?, ?, ?)""",
            (commande_id, ld["produit_id"], ld["quantite"], ld["prix_unitaire_estime"], ld["total_estime"])
        )

    conn.commit()
    
    return {
        "id": commande_id,
        "numero": numero,
        "statut": "En attente",
        "date_commande": today,
        "total_estime": total_estime,
        "lignes": []
    }
# ==========================================================
# 1. ROUTE GET : Récupérer l'historique des commandes du client
# ==========================================================
@router.get("", response_model=list[CommandeOut])
def get_mes_commandes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Retourne la liste des commandes passées par le client connecté,
    triées de la plus récente à la plus ancienne.
    """
    client_id = client["id"]

    # 1. Sélection des commandes du client
    cmd_rows = conn.execute(
        """SELECT * FROM commandes_clients
           WHERE client_id = ?
           ORDER BY id DESC
           LIMIT ? OFFSET ?""",
        (client_id, limit, offset),
    ).fetchall()

    commandes = []
    for c in cmd_rows:
        cmd_id = c["id"]

        # 2. Récupération des lignes de chaque commande
        lignes_rows = conn.execute(
            """SELECT l.*, p.designation
               FROM lignes_commande_client l
               LEFT JOIN produits p ON l.produit_id = p.id
               WHERE l.commande_id = ?""",
            (cmd_id,),
        ).fetchall()

        lignes = []
        for lr in lignes_rows:
            lignes.append(
                LigneCommandeOut(
                    produit_id=lr["produit_id"],
                    designation=lr["designation"] or "Article",
                    quantite=float(lr["quantite"] or 0),
                    prix_unitaire_estime=float(lr["prix_unitaire_estime"] or 0),
                    total_estime=float(lr["total_estime"] or 0),
                )
            )

        commandes.append(
            CommandeOut(
                id=cmd_id,
                numero=c["numero"] or f"CMD-{cmd_id}",
                date_commande=str(c["date_commande"] or ""),
                statut=c["statut"] or "En attente",
                total_estime=float(c["total_estime"] or 0.0),
                observations=c["observations"] if "observations" in c.keys() else None,
                bon_vente_id=c["bon_vente_id"] if "bon_vente_id" in c.keys() else None,
                lignes=lignes,
            )
        )

    return commandes