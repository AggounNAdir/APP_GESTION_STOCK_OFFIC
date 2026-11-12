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
from api.schemas import PointageGpsIn, PointageOut, VersementVendeurAdminIn, VersementVendeurAdminOut

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
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Liste des pointages terrain — destinée à un écran de supervision côté
    application bureau (suivi des tournées commerciales).
    """
    if vendeur_id is not None and vendeur_id != vendeur["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez consulter que vos propres pointages.",
        )

    query = "SELECT * FROM tournee_pointages WHERE vendeur_id=?"
    params: list = [vendeur["id"]]
    if client_id is not None:
        query += " AND client_id=?"
        params.append(client_id)
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


@router.get("/ventes")
def get_mes_ventes_terrain(
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retourne l'historique réel des ventes terrain du vendeur connecté."""
    rows = conn.execute(
        """SELECT b.id, b.numero, b.date_bon,
                  COALESCE(pc.nom, c.nom) AS client_nom,
                  b.total, COALESCE(b.montant_verse, 0) AS montant_verse,
                  COALESCE(b.reste_payer, 0) AS reste_payer, b.statut,
                  (SELECT COUNT(*) FROM lignes_vente l WHERE l.bon_id=b.id)
                      AS articles_count
           FROM bons_vente b
           LEFT JOIN prospects_clients pc ON pc.id=b.prospect_id
           LEFT JOIN clients c ON c.id=b.client_id
           WHERE b.vendeur_id=? AND b.numero LIKE 'BV-TERRAIN-%'
           ORDER BY b.id DESC LIMIT 200""",
        (vendeur["id"],),
    ).fetchall()
    return [dict(row) for row in rows]


@router.get("/ma-caisse")
def get_ma_caisse(
    date_debut: Optional[str] = Query(None, description="AAAA-MM-JJ"),
    date_fin: Optional[str] = Query(None, description="AAAA-MM-JJ"),
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Situation RÉELLE de caisse du vendeur connecté (calculée côté serveur).

    `reste_a_verser` = espèces encaissées (cumul) − remises validées par
    l'administration. Le vendeur ne peut pas modifier ce solde : la remise est
    enregistrée au bureau quand il remet l'argent.
    """
    from api import vendeur_dossier as dossier
    return dossier.caisse_vendeur(conn, vendeur["id"], date_debut, date_fin)


@router.get("/mes-remises")
def get_mes_remises(
    date_debut: Optional[str] = Query(None, description="AAAA-MM-JJ"),
    date_fin: Optional[str] = Query(None, description="AAAA-MM-JJ"),
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Historique des remises d'espèces du vendeur à l'administration."""
    from api import vendeur_dossier as dossier
    return dossier.versements_admin_vendeur(conn, vendeur["id"], date_debut, date_fin)


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
    """Crée une vente terrain, encaisse le montant reçu et débite le camion."""
    vendeur_id = vendeur["id"]
    today_str = date.today().isoformat()
    today_num = date.today().strftime("%Y%m%d")

    is_prospect = bool(
        payload.is_prospect
        or payload.prospect_id
        or (payload.code_client and payload.code_client.upper().startswith("PROSP"))
    )
    prospect_id = None
    if is_prospect:
        if payload.prospect_id:
            prospect = conn.execute(
                """SELECT id, nom, client_id, vendeur_id FROM prospects_clients
                   WHERE id=? AND (vendeur_id=? OR vendeur_id IS NULL)""",
                (payload.prospect_id, vendeur_id),
            ).fetchone()
        elif payload.code_client:
            prospect = conn.execute(
                """SELECT id, nom, client_id, vendeur_id FROM prospects_clients
                   WHERE code=? AND (vendeur_id=? OR vendeur_id IS NULL)""",
                (payload.code_client, vendeur_id),
            ).fetchone()
        else:
            prospect = None
        if prospect is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect introuvable ou non rattaché à ce vendeur.",
            )
        prospect_id = prospect["id"]
        client_id = prospect["client_id"]
        nom_affiche = prospect["nom"]
        if client_id is None:
            comptoir = conn.execute(
                "SELECT id FROM clients WHERE nom='COMPTOIR' ORDER BY id LIMIT 1"
            ).fetchone()
            if comptoir is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Le client COMPTOIR requis pour enregistrer la vente est introuvable.",
                )
            client_id = comptoir["id"]
    else:
        if payload.client_id:
            client = conn.execute(
                "SELECT id, nom FROM clients WHERE id=?", (payload.client_id,)
            ).fetchone()
        elif payload.code_client:
            client = conn.execute(
                "SELECT id, nom FROM clients WHERE code=?", (payload.code_client,)
            ).fetchone()
        else:
            client = None
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client introuvable.",
            )
        client_id = client["id"]
        nom_affiche = client["nom"]

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produit {l.produit_id} introuvable.",
            )

        f = float(p["facteur"] or 1)
        if f <= 0:
            f = 1.0
        qte_colis = float(l.quantite or 0)
        qte_pieces = qte_colis * f
        prix_unitaire = float(l.prix_unitaire if l.prix_unitaire is not None else (p["prix_vente"] or 0))
        if prix_unitaire < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le prix unitaire ne peut pas être négatif.",
            )
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
    if montant_verse > total_vente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le montant encaissé ne peut pas dépasser le total de la vente.",
        )
    reste_payer = round(total_vente - montant_verse, 2)

    with conn:
        if is_prospect and prospect["vendeur_id"] is None:
            cur_assign = conn.execute(
                """UPDATE prospects_clients SET vendeur_id=?
                   WHERE id=? AND vendeur_id IS NULL""",
                (vendeur_id, prospect_id),
            )
            if cur_assign.rowcount != 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ce prospect vient d'être attribué à un autre vendeur.",
                )

        # 1. Créer Bon de Vente
        cur = conn.execute(
            """INSERT INTO bons_vente
               (numero, date_bon, client_id, prospect_id, vendeur_id, total,
                montant_verse, reste_payer, statut, observations)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Validé', ?)""",
            (
                num_bv, today_str, client_id, prospect_id, vendeur_id,
                total_vente, montant_verse, reste_payer,
                payload.observations or "Vente directe terrain camion",
            ),
        )
        bon_vente_id = cur.lastrowid

        # 2. Insérer lignes de vente et décrémenter le stock camion
        for lv in lignes_validees:
            stock = conn.execute(
                """SELECT quantite_colis, quantite_pieces FROM stock_camion_vendeur
                   WHERE vendeur_id=? AND produit_id=?""",
                (vendeur_id, lv["produit_id"]),
            ).fetchone()
            if (
                stock is None
                or stock["quantite_colis"] < lv["qte_colis"] - 1e-9
                or stock["quantite_pieces"] < lv["qte_pieces"] - 1e-9
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Stock camion insuffisant pour {lv['designation']}.",
                )

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
                   WHERE vendeur_id = ? AND produit_id = ?
                     AND quantite_colis >= ? - 1e-9
                     AND quantite_pieces >= ? - 1e-9""",
                (
                    lv["qte_colis"], lv["qte_pieces"], vendeur_id,
                    lv["produit_id"], lv["qte_colis"], lv["qte_pieces"],
                ),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Le stock camion de {lv['designation']} a changé; réessayez.",
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
@router.post("/versement-admin", response_model=VersementVendeurAdminOut, status_code=status.HTTP_201_CREATED)
def enregistrer_versement_admin(
    payload: VersementVendeurAdminIn,
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Enregistre la remise d'espèces / versement effectué par le vendeur à la caisse de l'Admin.
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
        (numero, date_vers, vendeur["id"], payload.montant, payload.mode, payload.observations, date_vers)
    )
    conn.commit()

    return VersementVendeurAdminOut(
        id=cursor.lastrowid,
        numero=numero,
        date_vers=date_vers,
        vendeur_id=vendeur["id"],
        montant=payload.montant,
        mode=payload.mode,
        observations=payload.observations,
    )

@router.get("/versements-admin", response_model=list[VersementVendeurAdminOut])
def lister_versements_admin(
    vendeur: sqlite3.Row = Depends(get_current_vendeur),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Liste l'historique des versements remis par le vendeur à l'Admin."""
    rows = conn.execute(
        "SELECT * FROM versements_vendeurs_admin WHERE vendeur_id=? ORDER BY id DESC",
        (vendeur["id"],)
    ).fetchall()
    return [
        VersementVendeurAdminOut(
            id=r["id"],
            numero=r["numero"],
            date_vers=r["date_vers"],
            vendeur_id=r["vendeur_id"],
            montant=r["montant"],
            mode=r["mode"],
            observations=r["observations"],
        )
        for r in rows
    ]