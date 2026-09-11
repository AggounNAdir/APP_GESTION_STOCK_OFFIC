import sqlite3
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
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
    """Passe une nouvelle commande en ligne depuis le portail client."""
    client_id = client["id"]
    today = date.today().isoformat()

    count_today = conn.execute(
        "SELECT COUNT(*) FROM commandes_clients WHERE date_commande LIKE ?",
        (f"{today}%",)
    ).fetchone()[0]
    numero = f"CMD-{today.replace('-', '')}-{count_today + 1:04d}"

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
                detail=f"Produit ID {item.produit_id} introuvable ou inactif.",
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
           (numero, client_id, date_commande, statut, total_estime, observations)
           VALUES (?, ?, ?, 'En attente', ?, ?)""",
        (numero, client_id, today, total_estime, payload.observations)
    )
    commande_id = cursor.lastrowid

    out_lignes = []
    for ld in lignes_data:
        conn.execute(
            """INSERT INTO lignes_commande_client 
               (commande_id, produit_id, quantite, prix_unitaire_estime, total_estime)
               VALUES (?, ?, ?, ?, ?)""",
            (commande_id, ld["produit_id"], ld["quantite"], ld["prix_unitaire_estime"], ld["total_estime"])
        )
        out_lignes.append(
            LigneCommandeOut(
                produit_id=ld["produit_id"],
                designation=ld["designation"],
                quantite=ld["quantite"],
                prix_unitaire_estime=ld["prix_unitaire_estime"],
                total_estime=ld["total_estime"],
            )
        )

    conn.commit()

    return CommandeOut(
        id=commande_id,
        numero=numero,
        date_commande=today,
        statut="En attente",
        total_estime=total_estime,
        observations=payload.observations,
        bon_vente_id=None,
        lignes=out_lignes,
    )



@router.get("", response_model=list[CommandeOut])
def list_commandes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste l'historique des commandes passées par le client connecté."""
    rows = conn.execute(
        """SELECT * FROM commandes_clients WHERE client_id=?
           ORDER BY date_commande DESC, id DESC LIMIT ? OFFSET ?""",
        (client["id"], limit, offset),
    ).fetchall()

    result = []
    for r in rows:
        cmd_id = r["id"]
        lignes_rows = conn.execute(
            """SELECT l.*, p.designation FROM lignes_commande_client l
               LEFT JOIN produits p ON l.produit_id = p.id
               WHERE l.commande_id=?""",
            (cmd_id,),
        ).fetchall()

        out_lignes = [
            LigneCommandeOut(
                produit_id=lr["produit_id"],
                designation=lr["designation"] or "Article",
                quantite=float(lr["quantite"]),
                prix_unitaire_estime=float(lr["prix_unitaire_estime"]),
                total_estime=float(lr["total_estime"]),
            )
            for lr in lignes_rows
        ]

        result.append(
            CommandeOut(
                id=cmd_id,
                numero=r["numero"],
                date_commande=r["date_commande"],
                statut=r["statut"],
                total_estime=float(r["total_estime"] or 0),
                observations=r["observations"],
                bon_vente_id=r["bon_vente_id"],
                lignes=out_lignes,
            )
        )
    return result


@router.get("/{commande_id}", response_model=CommandeOut)
def get_commande_detail(
    commande_id: int,
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Détail d'une commande spécifique passée par le client."""
    r = conn.execute(
        "SELECT * FROM commandes_clients WHERE id=? AND client_id=?",
        (commande_id, client["id"]),
    ).fetchone()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable.",
        )

    lignes_rows = conn.execute(
        """SELECT l.*, p.designation FROM lignes_commande_client l
           LEFT JOIN produits p ON l.produit_id = p.id
           WHERE l.commande_id=?""",
            (commande_id,),
    ).fetchall()

    out_lignes = [
        LigneCommandeOut(
            produit_id=lr["produit_id"],
            designation=lr["designation"] or "Article",
            quantite=float(lr["quantite"]),
            prix_unitaire_estime=float(lr["prix_unitaire_estime"]),
            total_estime=float(lr["total_estime"]),
        )
        for lr in lignes_rows
    ]

    return CommandeOut(
        id=r["id"],
        numero=r["numero"],
        date_commande=r["date_commande"],
        statut=r["statut"],
        total_estime=float(r["total_estime"] or 0),
        observations=r["observations"],
        bon_vente_id=r["bon_vente_id"],
        lignes=out_lignes,
    )


@router.post("/{commande_id}/valider", response_model=CommandeOut)
def valider_commande(
    commande_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Valide une commande client et génère un bon de vente.
    Note: Cette fonction suppose que l'utilisateur est authentifié comme admin.
    """
    # 1. Récupérer la commande
    cmd = conn.execute("SELECT * FROM commandes_clients WHERE id=?", (commande_id,)).fetchone()
    if not cmd:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    if cmd["statut"] != "En attente":
        raise HTTPException(status_code=400, detail=f"La commande est déjà au statut '{cmd['statut']}'.")

    # 2. Générer le numéro de bon de vente (exemple simple)
    today = date.today().strftime("%Y%m%d")
    cursor_count = conn.execute("SELECT COUNT(*) FROM bons_vente WHERE date_bon LIKE ?", (f"{today}%",))
    count = cursor_count.fetchone()[0]
    num_bon = f"BV-{today}-{count + 1:04d}"

    # 3. Créer le Bon de Vente
    try:
        cursor = conn.execute(
            """INSERT INTO bons_vente (numero, date_bon, client_id, total, statut)
               VALUES (?, ?, ?, ?, 'Validé')""",
            (num_bon, date.today().isoformat(), cmd["client_id"], cmd["total_estime"])
        )
        bon_vente_id = cursor.lastrowid
        
        # 4. Transférer les lignes et mettre à jour le stock
        lignes = conn.execute("SELECT * FROM lignes_commande_client WHERE commande_id=?", (commande_id,)).fetchall()
        
        for l in lignes:
            # Insertion dans lignes_vente
            conn.execute(
                """INSERT INTO lignes_vente (bon_id, produit_id, quantite, prix_unitaire, total)
                   VALUES (?, ?, ?, ?, ?)""",
                (bon_vente_id, l["produit_id"], l["quantite"], l["prix_unitaire_estime"], l["total_estime"])
            )
            # Mise à jour du stock (via la fonction utilitaire du projet)
            from database import recalculer_cout_stock_apres_sortie
            recalculer_cout_stock_apres_sortie(conn, l["produit_id"], l["quantite"])

        # 5. Mettre à jour la commande client
        conn.execute(
            "UPDATE commandes_clients SET statut='Validée', bon_vente_id=? WHERE id=?",
            (bon_vente_id, commande_id)
        )
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la validation: {str(e)}")

    # Retourner la commande mise à jour (réutilisation de la logique de lecture)
    return get_commande_detail(commande_id, None, conn) # On passe None pour le client car on est dans un flux admin
