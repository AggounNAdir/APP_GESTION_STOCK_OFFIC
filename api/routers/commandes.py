"""
Router des Commandes — Portail Client & Tournée Vendeur (Silwane Androway)
Enregistrement direct SANS RECALCUL des montants calculés par le Portail Client :
  - Table 'commandes_clients' & 'lignes_commande_client' pour les Clients officiels
  - Table 'commandes_prospects' & 'lignes_commande_prospect' pour les Prospects terrain
"""
import sqlite3
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_current_client_or_vendeur, get_db, get_current_client
from api.schemas import CommandeIn, CommandeOut, LigneCommandeOut
from api.princing import controler_lignes_commande, resoudre_prix

router = APIRouter(prefix="/commandes", tags=["Commandes"])


@router.post("", response_model=CommandeOut, status_code=status.HTTP_201_CREATED)
def create_commande(
    payload: CommandeIn,
    auth: dict = Depends(get_current_client_or_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    today = date.today().isoformat()
    num_date = date.today().strftime("%Y%m%d")

    is_vendeur = (auth["type"] == "vendeur")

    # =========================================================================
    # 1. IDENTIFICATION DU DESTINATAIRE (CLIENT OFFICIEL OU PROSPECT TERRAIN)
    # =========================================================================
    if not is_vendeur:
        # Client connecté sur son portail web
        is_prospect = False
        target_client_id = auth["client"]["id"]
        target_prospect_id = None
        vendeur_id = payload.vendeur_id or (auth["client"]["vendeur_id"] if "vendeur_id" in auth["client"].keys() else None)
    else:
        # Vendeur connecté sur l'application mobile / tablette
        vendeur_id = auth["vendeur"]["id"]
        code = str(payload.code_client or "").strip().upper()
        nom = str(payload.nom_client or "").strip()

        is_prospect = bool(
            payload.is_prospect
            or code.startswith("PROSP")
            or (payload.prospect_id and payload.prospect_id > 0)
        )

        if is_prospect:
            target_client_id = None
            p_row = conn.execute(
                """SELECT id, nom FROM prospects_clients 
                   WHERE UPPER(TRIM(code)) = ? OR id = ? OR LOWER(TRIM(nom)) = ?""",
                (code, payload.prospect_id or 0, nom.lower())
            ).fetchone()
            target_prospect_id = p_row["id"] if p_row else (payload.prospect_id or 1)
        else:
            target_prospect_id = None
            target_client_id = payload.client_id
            if not target_client_id and code:
                c_row = conn.execute("SELECT id FROM clients WHERE UPPER(TRIM(code)) = ?", (code,)).fetchone()
                if c_row:
                    target_client_id = c_row["id"]
            if not target_client_id and nom:
                c_row = conn.execute("SELECT id FROM clients WHERE LOWER(TRIM(nom)) = ?", (nom.lower(),)).fetchone()
                if c_row:
                    target_client_id = c_row["id"]

            if not target_client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client introuvable. Veuillez préciser un client_id valide.",
                )

    # =========================================================================
    # 2. RÉCUPÉRATION DIRECTE DES LIGNES ET PRIX CALCULÉS PAR LE PORTAIL CLIENT
    # =========================================================================
    lignes_data = []
    somme_lignes = 0.0

    # Contrôle des prix reçus face au tarif du serveur (api/princing.py).
    # PRIX_CONTROLE_COMMANDES = off | warn (défaut : journalise seulement) | enforce (refuse).
    anomalies = controler_lignes_commande(
        conn, target_client_id, payload.lignes, est_vendeur=is_vendeur
    )
    bloquantes = [a.message for a in anomalies if a.bloquant]
    if bloquantes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prix non conforme au tarif : " + " ; ".join(bloquantes),
        )

    for item in payload.lignes:
        produit = conn.execute("SELECT designation, prix_vente FROM produits WHERE id=?", (item.produit_id,)).fetchone()
        designation = produit["designation"] if (produit and "designation" in produit.keys()) else f"Produit #{item.produit_id}"

        item_dict = item.model_dump() if hasattr(item, "model_dump") else item.dict()
        
        qte = float(item.quantite or 0)
        prix_unit = float(
            item_dict.get("prix_unitaire") 
            or item_dict.get("prix") 
            or getattr(item, "prix_unitaire", 0) 
            or getattr(item, "prix", 0) 
            # Aucun prix reçu : tarif du client (prix spécial > palier > niveau), pas prix_vente brut
            or resoudre_prix(
                conn, item.produit_id, client_id=target_client_id,
                quantite=qte * float(getattr(item, "facteur_conversion", 1) or 1),
            ).prix
        )
        
        # 🎯 PRENDRE DIRECTEMENT LE TOTAL TRANSMIS PAR LE PORTAIL CLIENT (calculé avec colisage)
        total_ligne = float(
            item_dict.get("total") 
            or item_dict.get("totalLigne") 
            or getattr(item, "total", None) 
            or getattr(item, "totalLigne", None) 
            or (qte * prix_unit)
        )
        somme_lignes += total_ligne

        lignes_data.append({
            "produit_id": item.produit_id,
            "designation": designation,
            "quantite": qte,
            "prix_unitaire": prix_unit,
            "total": total_ligne,
        })

    # Montant global calculé par le portail
    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    montant_total = float(
        payload_dict.get("montant_total") 
        or payload_dict.get("total") 
        or getattr(payload, "montant_total", None)
        or getattr(payload, "total", None)
        or somme_lignes
    )

    obs = payload.observations or ""

    # =========================================================================
    # 3. ENREGISTREMENT SQLITE (SÉCURISÉ)
    # =========================================================================
    if is_prospect:
        # --- CAS 1 : PROSPECT -> table 'commandes_prospects' ---
        # Tables commandes_prospects / lignes_commande_prospect : créées par api/schema.py
        cols_cp = [c[1] for c in conn.execute("PRAGMA table_info(commandes_prospects)").fetchall()]
        count = conn.execute(
            "SELECT COUNT(*) FROM commandes_prospects WHERE date_commande LIKE ?", (f"{date.today()}%",)
        ).fetchone()[0]
        numero = f"CMD-PROSP-{num_date}-{count + 1:04d}"

        if payload.nom_client:
            obs = f"[Prospect: {payload.nom_client}] {obs}".strip()

        col_montant_cmd = "montant_total" if "montant_total" in cols_cp else "total_estime"

        cursor = conn.execute(
            f"""INSERT INTO commandes_prospects 
               (numero, prospect_id, vendeur_id, date_commande, statut, {col_montant_cmd}, observations)
               VALUES (?, ?, ?, ?, 'En attente', ?, ?)""",
            (numero, target_prospect_id, vendeur_id, today, montant_total, obs)
        )
        commande_id = cursor.lastrowid

        cols_lignes = [c[1] for c in conn.execute("PRAGMA table_info(lignes_commande_prospect)").fetchall()]
        col_prix = "prix_unitaire" if "prix_unitaire" in cols_lignes else "prix_unitaire_estime"
        col_tot = "total" if "total" in cols_lignes else "total_estime"

        for ld in lignes_data:
            conn.execute(
                f"""INSERT INTO lignes_commande_prospect 
                   (commande_id, produit_id, quantite, {col_prix}, {col_tot})
                   VALUES (?, ?, ?, ?, ?)""",
                (commande_id, ld["produit_id"], ld["quantite"], ld["prix_unitaire"], ld["total"])
            )

        conn.commit()

    else:
        # --- CAS 2 : CLIENT OFFICIEL -> table 'commandes_clients' ---
        count = conn.execute(
            "SELECT COUNT(*) FROM commandes_clients WHERE date_commande LIKE ?", (f"{date.today()}%",)
        ).fetchone()[0]
        numero = f"CMD-{num_date}-{count + 1:04d}"

        cols_cc = [c[1] for c in conn.execute("PRAGMA table_info(commandes_clients)").fetchall()]
        col_montant_clt = "montant_total" if "montant_total" in cols_cc else "total_estime"

        cursor = conn.execute(
            f"""INSERT INTO commandes_clients 
               (numero, client_id, vendeur_id, date_commande, statut, {col_montant_clt}, observations)
               VALUES (?, ?, ?, ?, 'En attente', ?, ?)""",
            (numero, target_client_id, vendeur_id, today, montant_total, obs)
        )
        commande_id = cursor.lastrowid

        cols_lignes_c = [c[1] for c in conn.execute("PRAGMA table_info(lignes_commande_client)").fetchall()]
        col_prix_c = "prix_unitaire" if "prix_unitaire" in cols_lignes_c else "prix_unitaire_estime"
        col_tot_c = "total" if "total" in cols_lignes_c else "total_estime"

        for ld in lignes_data:
            conn.execute(
                f"""INSERT INTO lignes_commande_client 
                   (commande_id, produit_id, quantite, {col_prix_c}, {col_tot_c})
                   VALUES (?, ?, ?, ?, ?)""",
                (commande_id, ld["produit_id"], ld["quantite"], ld["prix_unitaire"], ld["total"])
            )

        conn.commit()

    # =========================================================================
    # 4. RÉPONSE JSON COMPLÈTE (conforme à CommandeOut)
    # =========================================================================
    return CommandeOut(
        id=commande_id,
        numero=numero,
        date_commande=today,
        statut="En attente",
        montant_total=montant_total,
        observations=obs,
        bon_vente_id=None,
        lignes=[
            LigneCommandeOut(
                produit_id=ld["produit_id"],
                designation=ld["designation"],
                quantite=ld["quantite"],
                prix_unitaire=ld["prix_unitaire"],
                total=ld["total"],
            )
            for ld in lignes_data
        ]
    )


# =========================================================================
# 5. HISTORIQUE DES COMMANDES DU CLIENT CONNECTÉ (conforme à list[CommandeOut])
# =========================================================================
# =========================================================================
# 5. HISTORIQUE DES COMMANDES DU CLIENT CONNECTÉ
# =========================================================================
@router.get("", response_model=list[CommandeOut])
def get_mes_commandes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
    client_id = client["id"]

    cmd_rows = conn.execute(
        """SELECT * FROM commandes_clients
           WHERE client_id = ?
           ORDER BY id DESC
           LIMIT ? OFFSET ?""",
        (client_id, limit, offset),
    ).fetchall()

    commandes = []
    for c in cmd_rows:
        c_dict = dict(c)
        cmd_id = c_dict["id"]
        
        montant = float(
            c_dict.get("montant_total") 
            or c_dict.get("total_estime") 
            or c_dict.get("total") 
            or 0.0
        )

        lignes_rows = conn.execute(
            """SELECT l.*, p.designation as p_designation ,p.facteur_conversion as p_facteur
               FROM lignes_commande_client l
               LEFT JOIN produits p ON l.produit_id = p.id
               WHERE l.commande_id = ?""",
            (cmd_id,),
        ).fetchall()

        lignes = []
        for lr in lignes_rows:
            lr_dict = dict(lr)  # 👈 Convertir en dictionnaire pour utiliser .get() en toute sécurité
            
            qte = float(lr_dict.get("quantite") or 0.0)
            
            # Récupération tolérante du prix unitaire
            prix = float(
                lr_dict.get("prix_unitaire") 
                or lr_dict.get("prix_unitaire_estime") 
                or lr_dict.get("prix") 
                or lr_dict.get("pu") 
                or 0.0
            )
            facteur = float(lr_dict.get("p_facteur") or lr_dict.get("facteur_conversion") or 1.0)
            # Récupération tolérante du total de la ligne
            tot = float(
                lr_dict.get("total") 
                or lr_dict.get("total_estime") 
                or lr_dict.get("montant") 
                or (qte * prix)
            )

            designation = lr_dict.get("p_designation") or lr_dict.get("designation") or "Article"

            lignes.append(
                LigneCommandeOut(
                    produit_id=lr_dict.get("produit_id", 0),
                    designation=designation,
                    quantite=qte,
                    prix_unitaire=prix,
                    facteur_conversion=facteur,
                    total=tot,
                )
            )

        commandes.append(
            CommandeOut(
                id=cmd_id,
                numero=c_dict.get("numero") or f"CMD-{cmd_id}",
                date_commande=str(c_dict.get("date_commande") or ""),
                statut=c_dict.get("statut") or "En attente",
                montant_total=montant,
                observations=c_dict.get("observations"),
                bon_vente_id=c_dict.get("bon_vente_id"),
                lignes=lignes,
            )
        )

    return commandes