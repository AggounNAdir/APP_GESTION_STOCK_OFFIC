"""
Router Tournée terrain — Silwane Androway.

Authentifié par le vendeur en tournée (voir api/deps.get_current_vendeur) :
le vendeur_id enregistré sur chaque pointage vient du jeton, jamais du
payload envoyé par le mobile, pour empêcher un vendeur de faire passer un
pointage sous l'identité d'un collègue.
"""
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status

from api.deps import get_db, get_current_vendeur
from api.schemas import PointageGpsIn, PointageOut

router = APIRouter(prefix="/tournee", tags=["Tournée Terrain (Androway)"])


def _enregistrer_pointage(
    conn: sqlite3.Connection, payload: PointageGpsIn, vendeur: sqlite3.Row
) -> PointageOut:
    data = payload.resolved()

    if data["client_id"] is None and not data["code_client"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id (ou clientId) requis pour enregistrer un pointage.",
        )

    # Si on a un client_id, on va chercher son code/nom réels pour ne pas
    # dépendre uniquement de ce que le mobile a mis en cache localement.
    code_client = data["code_client"]
    nom_client = data["nom_client"]
    if data["client_id"] is not None:
        row = conn.execute(
            "SELECT code, nom FROM clients WHERE id=?", (data["client_id"],)
        ).fetchone()
        if row is not None:
            code_client = row["code"]
            nom_client = row["nom"]

    date_pointage = data["date_pointage"] or datetime.now().isoformat(timespec="seconds")

    cursor = conn.execute(
        """INSERT INTO tournee_pointages
           (client_id, vendeur_id, code_client, nom_client, latitude, longitude, date_pointage, observations)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["client_id"],
            vendeur["id"],
            code_client,
            nom_client,
            data["latitude"],
            data["longitude"],
            date_pointage,
            data["observations"],
        ),
    )
    conn.commit()

    return PointageOut(
        id=cursor.lastrowid,
        client_id=data["client_id"],
        code_client=code_client,
        nom_client=nom_client,
        latitude=data["latitude"],
        longitude=data["longitude"],
        date_pointage=date_pointage,
        observations=data["observations"],
    )


@router.post("/pointage-gps", response_model=PointageOut, status_code=status.HTTP_201_CREATED)
def pointage_gps(
    payload: PointageGpsIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Appelé directement par gpsTourneeService.pointerPresenceVisite() : valide
    la présence du commercial chez le client avec preuve GPS immédiate.
    """
    return _enregistrer_pointage(conn, payload, vendeur)


@router.post("/pointage", response_model=PointageOut, status_code=status.HTTP_201_CREATED)
def pointage_offline(
    payload: PointageGpsIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Appelé via la file de synchronisation offline-first (androwaySyncService,
    opération de type 'pointageVisite') lorsque le mobile revient en ligne.
    Même logique métier que /pointage-gps ; endpoint séparé car c'est deux
    déclencheurs distincts côté portail.
    """
    return _enregistrer_pointage(conn, payload, vendeur)


@router.get("/pointages", response_model=list[PointageOut])
def list_pointages(
    client_id: Optional[int] = None,
    vendeur_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Liste des pointages terrain — destinée à un écran de supervision côté
    application bureau (suivi des tournées commerciales).
    """
    query = "SELECT * FROM tournee_pointages WHERE 1=1"
    params: list = []
    if client_id is not None:
        query += " AND client_id=?"
        params.append(client_id)
    if vendeur_id is not None:
        query += " AND vendeur_id=?"
        params.append(vendeur_id)
    query += " ORDER BY date_pointage DESC, id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = conn.execute(query, params).fetchall()
    return [
        PointageOut(
            id=r["id"],
            client_id=r["client_id"],
            code_client=r["code_client"],
            nom_client=r["nom_client"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            date_pointage=r["date_pointage"],
            observations=r["observations"],
        )
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════
# GESTION DU STOCK CAMION & CHARGEMENTS VENDEUR (Dépôt Central ↔ Camion)
# ═══════════════════════════════════════════════════════════════════════════

from api.schemas import StockCamionItem, ChargementIn, VenteTerrainIn
from api.stock_journal import enregistrer_mouvement
from datetime import date


@router.get("/stock-camion", response_model=list[StockCamionItem])
def get_mon_stock_camion(
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Récupère le stock individuel embarqué dans le camion du vendeur connecté,
    ainsi que le stock disponible à l'entrepôt central.
    """
    vendeur_id = vendeur["id"]
    query = """
        SELECT p.id as produit_id, p.code, p.designation, p.unite,
               COALESCE(p.facteur_conversion, 1) as facteur_conversion,
               p.prix_vente as prix_unitaire,
               COALESCE(p.stock_actuel, 0) as stock_depot_pieces,
               COALESCE(sc.quantite_colis, 0) as quantite_colis,
               COALESCE(sc.quantite_pieces, 0) as quantite_pieces
        FROM produits p
        LEFT JOIN stock_camion_vendeur sc ON sc.produit_id = p.id AND sc.vendeur_id = ?
        WHERE p.actif = 1
        ORDER BY p.designation ASC
    """
    rows = conn.execute(query, (vendeur_id,)).fetchall()
    result = []
    for r in rows:
        f = float(r["facteur_conversion"] or 1)
        if f <= 0:
            f = 1.0
        stock_depot_pieces = float(r["stock_depot_pieces"] or 0)
        stock_depot_colis = round(stock_depot_pieces / f, 2)
        qte_colis = float(r["quantite_colis"] or 0)
        qte_pieces = float(r["quantite_pieces"] or 0)

        result.append(
            StockCamionItem(
                produit_id=r["produit_id"],
                code=r["code"] or f"PRD-{r['produit_id']}",
                designation=r["designation"] or "",
                unite=r["unite"] or "Carton",
                facteur_conversion=f,
                prix_unitaire=float(r["prix_unitaire"] or 0),
                quantite_colis=qte_colis,
                quantite_pieces=qte_pieces,
                stock_depot_pieces=stock_depot_pieces,
                stock_depot_colis=stock_depot_colis,
            )
        )
    return result


@router.post("/chargement", status_code=status.HTTP_201_CREATED)
def enregistrer_chargement_camion(
    payload: ChargementIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Validation d'un Bon de Chargement (matin) :
    1. Décrémente le stock du dépôt central (produits.stock_actuel)
    2. Inscrit le transfert dans le journal des mouvements (CHARGEMENT_CAMION)
    3. Incrémente le stock camion individuel du vendeur (stock_camion_vendeur)
    """
    vendeur_id = vendeur["id"]
    today_str = date.today().isoformat()
    today_num = date.today().strftime("%Y%m%d")

    # Générer le numéro de bon
    cur_count = conn.execute("SELECT COUNT(*) FROM bons_chargement").fetchone()[0]
    num_bon = f"CHG-{today_num}-{(cur_count + 1):04d}"

    total_colis = sum(l.quantite_colis for l in payload.lignes if l.quantite_colis > 0)
    if total_colis <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le chargement doit contenir au moins un colis.",
        )

    with conn:
        cur = conn.execute(
            """INSERT INTO bons_chargement (numero, date_chargement, vendeur_id, statut, total_colis, observations)
               VALUES (?, ?, ?, 'Validé', ?, ?)""",
            (num_bon, today_str, vendeur_id, total_colis, payload.observations or "Chargement tournée matin"),
        )
        chg_id = cur.lastrowid

        total_pieces_chg = 0.0
        for l in payload.lignes:
            if l.quantite_colis <= 0:
                continue

            prod = conn.execute(
                "SELECT id, designation, stock_actuel, COALESCE(facteur_conversion, 1) as facteur FROM produits WHERE id=?",
                (l.produit_id,),
            ).fetchone()
            if not prod:
                continue

            f = float(prod["facteur"] or 1)
            if f <= 0:
                f = 1.0
            qte_pieces = l.quantite_colis * f
            total_pieces_chg += qte_pieces

            # 1. Enregistrer ligne de chargement
            conn.execute(
                """INSERT INTO lignes_chargement (chargement_id, produit_id, quantite_colis, quantite_pieces)
                   VALUES (?, ?, ?, ?)""",
                (chg_id, l.produit_id, l.quantite_colis, qte_pieces),
            )

            # 2. Sortir du stock du dépôt central
            stock_avant = float(prod["stock_actuel"] or 0)
            stock_apres = max(0.0, stock_avant - qte_pieces)
            conn.execute("UPDATE produits SET stock_actuel = ? WHERE id = ?", (stock_apres, l.produit_id))

            # 3. Journal des mouvements
            try:
                enregistrer_mouvement(
                    conn,
                    l.produit_id,
                    "CHARGEMENT_CAMION",
                    stock_avant,
                    stock_apres,
                    quantite=-qte_pieces,
                    document_type="bon_chargement",
                    document_id=chg_id,
                    document_numero=num_bon,
                    tiers_nom=vendeur["nom"],
                    motif=f"Chargement camion {vendeur['nom']} ({l.quantite_colis} colis)",
                    utilisateur=vendeur["nom"],
                )
            except Exception as e:
                # Si erreur journal, continuer
                pass

            # 4. Ajouter au stock camion du vendeur
            conn.execute(
                """INSERT INTO stock_camion_vendeur (vendeur_id, produit_id, quantite_colis, quantite_pieces, date_maj)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(vendeur_id, produit_id)
                   DO UPDATE SET 
                       quantite_colis = quantite_colis + excluded.quantite_colis,
                       quantite_pieces = quantite_pieces + excluded.quantite_pieces,
                       date_maj = datetime('now')""",
                (vendeur_id, l.produit_id, l.quantite_colis, qte_pieces),
            )

        conn.execute("UPDATE bons_chargement SET total_pieces = ? WHERE id = ?", (total_pieces_chg, chg_id))

    return {
        "status": "success",
        "numero": num_bon,
        "chargement_id": chg_id,
        "total_colis": total_colis,
        "message": f"Chargement {num_bon} validé ({total_colis} colis chargés dans le camion).",
    }


@router.post("/dechargement")
def decharger_camion(
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Déchargement du camion (soir) :
    Réintègre les colis non vendus du camion vers le dépôt central et remet le camion à zéro.
    """
    vendeur_id = vendeur["id"]
    stk_rows = conn.execute(
        "SELECT produit_id, quantite_colis, quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND (quantite_colis > 0 OR quantite_pieces > 0)",
        (vendeur_id,),
    ).fetchall()

    if not stk_rows:
        return {"status": "ok", "message": "Le camion est déjà vide."}

    with conn:
        for r in stk_rows:
            p_id = r["produit_id"]
            pieces_retour = float(r["quantite_pieces"] or 0)
            colis_retour = float(r["quantite_colis"] or 0)

            # Réintégrer au dépôt
            prod = conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (p_id,)).fetchone()
            stock_avant = float(prod["stock_actuel"] or 0) if prod else 0.0
            stock_apres = stock_avant + pieces_retour

            conn.execute("UPDATE produits SET stock_actuel = ? WHERE id = ?", (stock_apres, p_id))

            # Remettre camion à 0
            conn.execute(
                "UPDATE stock_camion_vendeur SET quantite_colis = 0, quantite_pieces = 0, date_maj = datetime('now') WHERE vendeur_id=? AND produit_id=?",
                (vendeur_id, p_id),
            )

            # Journaliser
            try:
                enregistrer_mouvement(
                    conn,
                    p_id,
                    "RETOUR_CAMION",
                    stock_avant,
                    stock_apres,
                    quantite=pieces_retour,
                    motif=f"Déchargement fin de tournée {vendeur['nom']} ({colis_retour} colis)",
                    utilisateur=vendeur["nom"],
                )
            except Exception:
                pass

    return {"status": "success", "message": f"Camion déchargé. Marchandises réintégrées au dépôt central."}


@router.post("/vente-directe", status_code=status.HTTP_201_CREATED)
def valider_vente_directe_terrain(
    payload: VenteTerrainIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Vente directe sur le terrain (livré et encaissé immédiatement) :
    1. Décrémente le stock individuel du camion (stock_camion_vendeur)
    2. Crée le Bon de Vente (bons_vente & lignes_vente)
    3. Met à jour le solde du client ou du prospect
    4. Si un versement est effectué, enregistre l'encaissement
    """
    vendeur_id = vendeur["id"]
    today_str = date.today().isoformat()
    today_num = date.today().strftime("%Y%m%d")

    # Résolution client ou prospect
    is_prospect = bool(payload.is_prospect or (payload.code_client and payload.code_client.upper().startswith("PROSP")))
    client_id = payload.client_id
    prospect_id = payload.prospect_id

    nom_affiche = payload.nom_client or "Client Terrain"

    if is_prospect:
        if not prospect_id and payload.code_client:
            p_row = conn.execute("SELECT id, nom FROM prospects_clients WHERE code=?", (payload.code_client,)).fetchone()
            if p_row:
                prospect_id = p_row["id"]
                nom_affiche = p_row["nom"]
    else:
        if not client_id and payload.code_client:
            c_row = conn.execute("SELECT id, nom FROM clients WHERE code=?", (payload.code_client,)).fetchone()
            if c_row:
                client_id = c_row["id"]
                nom_affiche = c_row["nom"]

    # Numéro Bon de Vente
    cur_bv = conn.execute("SELECT COUNT(*) FROM bons_vente").fetchone()[0]
    num_bv = f"BV-TERRAIN-{today_num}-{(cur_bv + 1):04d}"

    total_vente = 0.0
    lignes_validees = []

    for l in payload.lignes:
        p = conn.execute(
            "SELECT id, designation, prix_vente, COALESCE(facteur_conversion, 1) as facteur FROM produits WHERE id=?",
            (l.produit_id,),
        ).fetchone()
        if not p:
            continue

        f = float(p["facteur"] or 1)
        if f <= 0:
            f = 1.0
        qte_colis = float(l.quantite or 0)
        qte_pieces = qte_colis * f
        prix_unitaire = float(l.prix_unitaire if l.prix_unitaire is not None else (p["prix_vente"] or 0))
        total_ligne = round(qte_pieces * prix_unitaire, 2)
        total_vente += total_ligne

        lignes_validees.append({
            "produit_id": l.produit_id,
            "designation": p["designation"],
            "qte_colis": qte_colis,
            "qte_pieces": qte_pieces,
            "prix_unitaire": prix_unitaire,
            "total": total_ligne,
        })

    if not lignes_validees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La vente doit contenir au moins un produit.",
        )

    montant_verse = float(payload.montant_verse or 0.0)
    reste_payer = max(0.0, total_vente - montant_verse)

    with conn:
        # 1. Créer Bon de Vente
        cur = conn.execute(
            """INSERT INTO bons_vente (numero, date_bon, client_id, vendeur_id, total, montant_verse, reste_payer, statut, observations)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Validé', ?)""",
            (num_bv, today_str, client_id or 1, vendeur_id, total_vente, montant_verse, reste_payer, payload.observations or "Vente directe terrain camion"),
        )
        bon_vente_id = cur.lastrowid

        # 2. Insérer lignes de vente et décrémenter le stock camion
        for lv in lignes_validees:
            conn.execute(
                """INSERT INTO lignes_vente (bon_id, produit_id, quantite, prix_unitaire, total)
                   VALUES (?, ?, ?, ?, ?)""",
                (bon_vente_id, lv["produit_id"], lv["qte_pieces"], lv["prix_unitaire"], lv["total"]),
            )

            # Décrémenter le stock camion du vendeur
            conn.execute(
                """UPDATE stock_camion_vendeur
                   SET quantite_colis = MAX(0, quantite_colis - ?),
                       quantite_pieces = MAX(0, quantite_pieces - ?),
                       date_maj = datetime('now')
                   WHERE vendeur_id = ? AND produit_id = ?""",
                (lv["qte_colis"], lv["qte_pieces"], vendeur_id, lv["produit_id"]),
            )

        # 3. Mettre à jour solde du tiers (créance)
        if reste_payer > 0:
            if is_prospect and prospect_id:
                conn.execute("UPDATE prospects_clients SET solde = COALESCE(solde, 0) + ? WHERE id = ?", (reste_payer, prospect_id))
            elif client_id:
                conn.execute("UPDATE clients SET solde = COALESCE(solde, 0) + ? WHERE id = ?", (reste_payer, client_id))

        # 4. Si montant versé > 0, enregistrer le versement
        if montant_verse > 0:
            num_vers = f"VR-TERRAIN-{today_num}-{(cur_bv + 1):04d}"
            if is_prospect and prospect_id:
                conn.execute(
                    """INSERT INTO versements_prospects (numero, date_vers, prospect_id, montant, mode, vendeur_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (num_vers, today_str, prospect_id, montant_verse, payload.mode_reglement or "Espèces", vendeur_id),
                )
            elif client_id:
                conn.execute(
                    """INSERT INTO versements_clients (numero, date_vers, client_id, montant, mode, vendeur_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (num_vers, today_str, client_id, montant_verse, payload.mode_reglement or "Espèces", vendeur_id),
                )

    return {
        "status": "success",
        "numero": num_bv,
        "bon_vente_id": bon_vente_id,
        "total": total_vente,
        "montant_verse": montant_verse,
        "reste_payer": reste_payer,
        "nom_client": nom_affiche,
        "message": f"Vente directe {num_bv} validée et stock camion déduit !",
    }