import sqlite3
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from api.deps import get_db, get_current_client
from api.schemas import CommandeIn, CommandeOut, LigneCommandeOut
from api.princing import resolve_prix

router = APIRouter(prefix="/commandes", tags=["Commandes Portail"])

@router.post("", response_model=CommandeOut, status_code=status.HTTP_201_CREATED)
def create_commande(
    payload: CommandeIn,
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    client_id = payload.client_id or client["id"]
    vendeur_id = payload.vendeur_id
    
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
    
    # Remplacer par un retour complet si nécessaire
    return {"id": commande_id, "numero": numero, "statut": "En attente", "date_commande": today, "total_estime": total_estime, "lignes": []}

"" 
