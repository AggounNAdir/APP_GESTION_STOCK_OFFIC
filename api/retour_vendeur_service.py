"""Retours de marchandise des vendeurs (camion -> dépôt), avec confirmation de l'administration.

Circuit :
  1. Le vendeur déclare ce qu'il rapporte : produit, quantité, MOTIF, et qui l'a rapporté
     -> demande « En attente » (rien ne bouge).
  2. L'administration CONFIRME (ou rejette) :
       - le stock du camion du vendeur baisse de la quantité retournée ;
       - la marchandise entre dans la zone « retours à traiter » du dépôt
         (produits.stock_retours_pieces), elle n'est PAS encore vendable ;
       - la situation du vendeur est ajustée (colis retournés, camion en baisse).
  3. L'administration décide du sort de chaque ligne :
       - VENDABLE    -> réintègre le stock vendable (journal RETOUR_CAMION) ;
       - CASSE       -> perte valorisée, imputée au VENDEUR ou à l'ENTREPRISE
                        (journal RETOUR_CAMION puis CASSE_CAMION) ;
       - FOURNISSEUR -> sort du stock, à renvoyer au fournisseur
                        (journal RETOUR_CAMION puis RETOUR_ACHAT).
Ainsi chaque pièce reste localisable : camion, retours à traiter, vendable, casse, fournisseur.
Quantités stockées en pièces ; saisies en colis. Aucun commit hors des blocs `with conn`.
"""
import math
from datetime import date, datetime
import sqlite3
from typing import Iterable, Optional

from api.stock_journal import enregistrer_mouvement

STATUT_ATTENTE = "En attente"
STATUT_CONFIRME = "Confirmé"
STATUT_REJETE = "Rejeté"
STATUT_ANNULE = "Annulé"

MOTIFS = {
    "INVENDU": "Invendu",
    "CASSE": "Cassé / abîmé",
    "PERIME": "Périmé / date courte",
    "ERREUR_CHARGEMENT": "Erreur de chargement",
    "RETOUR_CLIENT": "Repris chez un client",
    "AUTRE": "Autre (préciser)",
}
DECISIONS = {
    "VENDABLE": "Remis en stock vendable",
    "CASSE": "Casse",
    "FOURNISSEUR": "À retourner au fournisseur",
}
IMPUTATIONS = {"VENDEUR": "Imputée au vendeur", "ENTREPRISE": "Perte de l'entreprise"}
_EPS = 1e-6


def _facteur(valeur) -> float:
    try:
        f = float(valeur or 1)
    except (TypeError, ValueError):
        return 1.0
    return f if math.isfinite(f) and f > 0 else 1.0


def _numero(conn: sqlite3.Connection) -> str:
    jour = date.today().strftime("%Y%m%d")
    n = conn.execute("SELECT COUNT(*) FROM retours_vendeur WHERE numero LIKE ?", (f"RTV-{jour}-%",)).fetchone()[0]
    while True:
        n += 1
        numero = f"RTV-{jour}-{n:04d}"
        if conn.execute("SELECT 1 FROM retours_vendeur WHERE numero=?", (numero,)).fetchone() is None:
            return numero


def _camion_pieces(conn, vendeur_id: int, produit_id: int) -> float:
    r = conn.execute(
        "SELECT quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
        (vendeur_id, produit_id),
    ).fetchone()
    return float(r["quantite_pieces"] or 0) if r else 0.0


def _deja_demande(conn, vendeur_id: int, produit_id: int, hors_retour: Optional[int] = None) -> float:
    """Pièces de ce produit déjà promises par d'autres demandes en attente du même vendeur."""
    sql = """SELECT COALESCE(SUM(l.quantite_pieces), 0) FROM lignes_retour_vendeur l
             JOIN retours_vendeur r ON r.id = l.retour_id
             WHERE r.vendeur_id=? AND l.produit_id=? AND r.statut=?"""
    params: list = [vendeur_id, produit_id, STATUT_ATTENTE]
    if hors_retour is not None:
        sql += " AND r.id<>?"
        params.append(hors_retour)
    return float(conn.execute(sql, params).fetchone()[0] or 0)


# ───────────────────────────── 1. demande du vendeur ─────────────────────────────

def creer_demande_retour(
    conn: sqlite3.Connection,
    vendeur_id: int,
    lignes: Iterable[tuple],
    retourne_par: str = "",
    observations: str = "",
) -> dict:
    """`lignes` : (produit_id, colis, motif[, commentaire]). Un produit peut figurer
    plusieurs fois avec des motifs différents (ex. 3 invendus + 1 cassé)."""
    saisie = []
    for ligne in lignes:
        produit_id, colis, motif = int(ligne[0]), float(ligne[1]), str(ligne[2] or "").strip().upper()
        commentaire = (ligne[3] if len(ligne) > 3 else "") or ""
        commentaire = str(commentaire).strip()
        if not math.isfinite(colis) or colis <= 0:
            raise ValueError("Chaque quantité retournée doit être supérieure à zéro.")
        if motif not in MOTIFS:
            raise ValueError("Le motif du retour est obligatoire (invendu, cassé, périmé…).")
        if motif == "AUTRE" and not commentaire:
            raise ValueError("Motif « Autre » : précisez la raison dans le commentaire.")
        saisie.append((produit_id, colis, motif, commentaire))
    if not saisie:
        raise ValueError("Le retour doit contenir au moins un produit.")

    with conn:
        vendeur = conn.execute("SELECT id, nom FROM vendeurs WHERE id=? AND actif=1", (vendeur_id,)).fetchone()
        if vendeur is None:
            raise ValueError("Le vendeur sélectionné n'existe pas ou est désactivé.")
        retourne_par = (retourne_par or "").strip() or vendeur["nom"]

        details, total_par_produit = [], {}
        for produit_id, colis, motif, commentaire in saisie:
            p = conn.execute(
                """SELECT id, designation, COALESCE(facteur_conversion, 1) AS facteur,
                          COALESCE(prix_achat, 0) AS prix_achat, COALESCE(prix_vente, 0) AS prix_vente
                   FROM produits WHERE id=? AND actif=1""", (produit_id,),
            ).fetchone()
            if p is None:
                raise ValueError(f"Le produit #{produit_id} n'existe pas ou est désactivé.")
            facteur = _facteur(p["facteur"])
            pieces = round(colis * facteur, 6)
            total_par_produit[produit_id] = total_par_produit.get(produit_id, 0.0) + pieces
            dispo = _camion_pieces(conn, vendeur_id, produit_id) - _deja_demande(conn, vendeur_id, produit_id)
            if total_par_produit[produit_id] > dispo + _EPS:
                raise ValueError(
                    f"{p['designation']} : retour de {total_par_produit[produit_id] / facteur:g} colis, "
                    f"mais seulement {max(dispo, 0) / facteur:g} disponible(s) dans le camion "
                    "(hors autres demandes en attente)."
                )
            details.append((produit_id, facteur, pieces, motif, commentaire or None,
                            float(p["prix_achat"]), float(p["prix_vente"])))

        numero = _numero(conn)
        cur = conn.execute(
            """INSERT INTO retours_vendeur (numero, date_demande, vendeur_id, retourne_par, statut, observations)
               VALUES (?,?,?,?,?,?)""",
            (numero, datetime.now().isoformat(timespec="seconds"), vendeur_id, retourne_par,
             STATUT_ATTENTE, (observations or "").strip() or None),
        )
        retour_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO lignes_retour_vendeur
               (retour_id, produit_id, facteur, quantite_pieces, motif, commentaire, prix_achat, prix_vente)
               VALUES (?,?,?,?,?,?,?,?)""",
            [(retour_id, *d) for d in details],
        )
    return detail_retour(conn, retour_id)


def annuler_demande_retour(conn: sqlite3.Connection, retour_id: int, vendeur_id: int) -> dict:
    """Le vendeur retire sa demande tant que l'administration ne l'a pas traitée."""
    with conn:
        r = conn.execute("SELECT statut FROM retours_vendeur WHERE id=? AND vendeur_id=?", (retour_id, vendeur_id)).fetchone()
        if r is None:
            raise ValueError("Retour introuvable.")
        if r["statut"] != STATUT_ATTENTE:
            raise ValueError(f"Ce retour est déjà « {r['statut']} » : il ne peut plus être annulé.")
        conn.execute("UPDATE retours_vendeur SET statut=?, date_decision=? WHERE id=?",
                     (STATUT_ANNULE, datetime.now().isoformat(timespec="seconds"), retour_id))
    return detail_retour(conn, retour_id)


# ───────────────────────────── 2. confirmation admin ─────────────────────────────

def confirmer_retour(conn: sqlite3.Connection, retour_id: int, utilisateur: str = "") -> dict:
    """Confirme le retour : le camion baisse, la marchandise passe en « retours à traiter »."""
    with conn:
        r = conn.execute("SELECT * FROM retours_vendeur WHERE id=?", (retour_id,)).fetchone()
        if r is None:
            raise ValueError("Retour introuvable.")
        if r["statut"] != STATUT_ATTENTE:
            raise ValueError(f"Ce retour est déjà « {r['statut']} » : il ne peut plus être confirmé.")
        lignes = conn.execute(
            """SELECT l.*, p.designation FROM lignes_retour_vendeur l
               JOIN produits p ON p.id = l.produit_id WHERE l.retour_id=?""", (retour_id,),
        ).fetchall()

        par_produit: dict[int, float] = {}
        noms: dict[int, str] = {}
        for l in lignes:
            par_produit[l["produit_id"]] = par_produit.get(l["produit_id"], 0.0) + float(l["quantite_pieces"])
            noms[l["produit_id"]] = l["designation"]
        for pid, pieces in par_produit.items():
            dispo = _camion_pieces(conn, r["vendeur_id"], pid)
            if pieces > dispo + _EPS:
                raise ValueError(
                    f"Le camion ne contient plus assez de {noms[pid]} ({dispo:g} pièce(s) au lieu de "
                    f"{pieces:g}). Rejetez ce retour et demandez au vendeur d'en refaire un."
                )

        facteurs = {l["produit_id"]: _facteur(l["facteur"]) for l in lignes}
        for pid, pieces in par_produit.items():
            reste = round(_camion_pieces(conn, r["vendeur_id"], pid) - pieces, 6)
            reste = 0.0 if abs(reste) < _EPS else reste
            conn.execute(
                """UPDATE stock_camion_vendeur SET quantite_pieces=?, quantite_colis=?, date_maj=datetime('now')
                   WHERE vendeur_id=? AND produit_id=?""",
                (reste, round(reste / facteurs[pid], 6), r["vendeur_id"], pid),
            )
            conn.execute(
                "UPDATE produits SET stock_retours_pieces = COALESCE(stock_retours_pieces, 0) + ? WHERE id=?",
                (pieces, pid),
            )
        conn.execute(
            "UPDATE retours_vendeur SET statut=?, date_decision=?, decide_par=? WHERE id=?",
            (STATUT_CONFIRME, datetime.now().isoformat(timespec="seconds"), utilisateur or None, retour_id),
        )
    return detail_retour(conn, retour_id)


def rejeter_retour(conn: sqlite3.Connection, retour_id: int, utilisateur: str, motif: str) -> dict:
    motif = (motif or "").strip()
    if not motif:
        raise ValueError("Le motif du rejet est obligatoire.")
    with conn:
        r = conn.execute("SELECT statut FROM retours_vendeur WHERE id=?", (retour_id,)).fetchone()
        if r is None:
            raise ValueError("Retour introuvable.")
        if r["statut"] != STATUT_ATTENTE:
            raise ValueError(f"Ce retour est déjà « {r['statut']} » : il ne peut plus être rejeté.")
        conn.execute(
            "UPDATE retours_vendeur SET statut=?, date_decision=?, decide_par=?, motif_rejet=? WHERE id=?",
            (STATUT_REJETE, datetime.now().isoformat(timespec="seconds"), utilisateur or None, motif, retour_id),
        )
    return detail_retour(conn, retour_id)


# ───────────────────────────── 3. sort de la marchandise ─────────────────────────────

def decider_ligne(
    conn: sqlite3.Connection,
    ligne_id: int,
    decision: str,
    utilisateur: str = "",
    imputation: Optional[str] = None,
) -> dict:
    """Décide du sort d'une ligne confirmée (décision définitive). Casse : imputation obligatoire."""
    decision = (decision or "").strip().upper()
    imputation = (imputation or "").strip().upper() or None
    if decision not in DECISIONS:
        raise ValueError(f"Décision inconnue : {decision!r}.")
    if decision == "CASSE" and imputation not in IMPUTATIONS:
        raise ValueError("Casse : indiquez si la perte est imputée au vendeur ou à l'entreprise.")
    if decision != "CASSE":
        imputation = None

    with conn:
        l = conn.execute(
            """SELECT l.*, r.statut, r.numero, r.vendeur_id, r.retourne_par, v.nom AS vendeur_nom,
                      p.stock_actuel, COALESCE(p.stock_retours_pieces, 0) AS tampon
               FROM lignes_retour_vendeur l
               JOIN retours_vendeur r ON r.id = l.retour_id
               LEFT JOIN vendeurs v ON v.id = r.vendeur_id
               JOIN produits p ON p.id = l.produit_id WHERE l.id=?""", (ligne_id,),
        ).fetchone()
        if l is None:
            raise ValueError("Ligne de retour introuvable.")
        if l["statut"] != STATUT_CONFIRME:
            raise ValueError("Le retour doit d'abord être confirmé avant de décider du sort des produits.")
        if l["decision"] is not None:
            raise ValueError("Une décision a déjà été prise pour cette ligne.")
        pieces = float(l["quantite_pieces"])
        if float(l["tampon"]) + _EPS < pieces:
            raise ValueError("La zone « retours à traiter » ne contient pas cette quantité : incohérence à vérifier.")

        facteur = _facteur(l["facteur"])
        stock_avant = float(l["stock_actuel"] or 0)
        apres_retour = stock_avant + pieces
        libelle_motif = MOTIFS.get(l["motif"], l["motif"])
        doc = dict(document_type="retour_vendeur", document_id=l["retour_id"], document_numero=l["numero"],
                   tiers_nom=l["vendeur_nom"], utilisateur=utilisateur or None)
        origine = f"Retour vendeur {l['vendeur_nom']} (rapporté par {l['retourne_par']}) — {libelle_motif}"

        # tout ce qui revient entre au journal ; ce qui n'est pas vendable en ressort aussitôt
        enregistrer_mouvement(conn, l["produit_id"], "RETOUR_CAMION", stock_avant, apres_retour,
                              quantite=pieces, motif=origine, **doc)
        if decision == "VENDABLE":
            stock_apres = apres_retour
        elif decision == "CASSE":
            stock_apres = stock_avant
            enregistrer_mouvement(conn, l["produit_id"], "CASSE_CAMION", apres_retour, stock_apres,
                                  quantite=-pieces, motif=f"Casse — {IMPUTATIONS[imputation]} — {libelle_motif}", **doc)
        else:
            stock_apres = stock_avant
            enregistrer_mouvement(conn, l["produit_id"], "RETOUR_ACHAT", apres_retour, stock_apres,
                                  quantite=-pieces, motif=f"À retourner au fournisseur — {libelle_motif}", **doc)

        conn.execute(
            "UPDATE produits SET stock_actuel=?, stock_retours_pieces = COALESCE(stock_retours_pieces, 0) - ? WHERE id=?",
            (stock_apres, pieces, l["produit_id"]),
        )
        perte = round(pieces * float(l["prix_achat"] or 0), 2) if decision == "CASSE" else 0.0
        conn.execute(
            """UPDATE lignes_retour_vendeur
               SET decision=?, imputation=?, valeur_perte=?, decision_par=?, date_decision=? WHERE id=?""",
            (decision, imputation, perte, utilisateur or None, datetime.now().isoformat(timespec="seconds"), ligne_id),
        )
    return {"ligne_id": ligne_id, "decision": decision, "imputation": imputation,
            "pieces": pieces, "colis": round(pieces / facteur, 4), "valeur_perte": perte}


# ───────────────────────────── consultation ─────────────────────────────

def detail_retour(conn: sqlite3.Connection, retour_id: int) -> dict:
    r = conn.execute(
        """SELECT r.*, v.nom AS vendeur_nom FROM retours_vendeur r
           LEFT JOIN vendeurs v ON v.id = r.vendeur_id WHERE r.id=?""", (retour_id,),
    ).fetchone()
    if r is None:
        raise ValueError("Retour introuvable.")
    res = dict(r)
    res["lignes"] = []
    for l in conn.execute(
        """SELECT l.id, l.produit_id, p.code, p.designation, l.facteur, l.quantite_pieces, l.motif,
                  l.commentaire, l.prix_achat, l.prix_vente, l.decision, l.imputation, l.valeur_perte,
                  l.decision_par, l.date_decision
           FROM lignes_retour_vendeur l JOIN produits p ON p.id = l.produit_id
           WHERE l.retour_id=? ORDER BY l.id""", (retour_id,),
    ).fetchall():
        d = dict(l)
        d["colis"] = round(d["quantite_pieces"] / _facteur(d["facteur"]), 4)
        d["motif_libelle"] = MOTIFS.get(d["motif"], d["motif"])
        d["decision_libelle"] = DECISIONS.get(d["decision"]) if d["decision"] else None
        res["lignes"].append(d)
    res["total_pieces"] = sum(x["quantite_pieces"] for x in res["lignes"])
    res["total_colis"] = round(sum(x["colis"] for x in res["lignes"]), 4)
    return res


def lister_retours(conn: sqlite3.Connection, vendeur_id: Optional[int] = None,
                   statut: Optional[str] = None, limite: int = 100) -> list:
    sql = """SELECT r.id, r.numero, r.date_demande, r.vendeur_id, v.nom AS vendeur_nom, r.retourne_par, r.statut,
                    r.observations, r.date_decision, r.decide_par, r.motif_rejet,
                    COUNT(l.id) AS nb_lignes, COALESCE(SUM(l.quantite_pieces / COALESCE(NULLIF(l.facteur, 0), 1)), 0) AS total_colis,
                    COALESCE(SUM(l.quantite_pieces), 0) AS total_pieces,
                    COALESCE(SUM(CASE WHEN l.decision IS NULL THEN 1 ELSE 0 END), 0) AS lignes_a_decider
             FROM retours_vendeur r
             LEFT JOIN vendeurs v ON v.id = r.vendeur_id
             LEFT JOIN lignes_retour_vendeur l ON l.retour_id = r.id WHERE 1=1"""
    params: list = []
    if vendeur_id is not None:
        sql += " AND r.vendeur_id=?"
        params.append(vendeur_id)
    if statut:
        sql += " AND r.statut=?"
        params.append(statut)
    sql += " GROUP BY r.id ORDER BY r.id DESC LIMIT ?"
    params.append(int(limite))
    return [dict(x) for x in conn.execute(sql, params).fetchall()]


def lignes_a_traiter(conn: sqlite3.Connection) -> list:
    """Produits retournés et confirmés, en attente de décision (zone « retours à traiter »)."""
    rows = conn.execute(
        """SELECT l.id, r.id AS retour_id, r.numero, r.vendeur_id, v.nom AS vendeur_nom, r.retourne_par,
                  r.date_decision AS date_confirmation, p.code, p.designation, l.facteur, l.quantite_pieces,
                  l.motif, l.commentaire, l.prix_achat
           FROM lignes_retour_vendeur l
           JOIN retours_vendeur r ON r.id = l.retour_id
           LEFT JOIN vendeurs v ON v.id = r.vendeur_id
           JOIN produits p ON p.id = l.produit_id
           WHERE r.statut=? AND l.decision IS NULL ORDER BY r.date_decision, l.id""",
        (STATUT_CONFIRME,),
    ).fetchall()
    out = []
    for x in rows:
        d = dict(x)
        d["colis"] = round(d["quantite_pieces"] / _facteur(d["facteur"]), 4)
        d["motif_libelle"] = MOTIFS.get(d["motif"], d["motif"])
        out.append(d)
    return out


def compter_a_traiter(conn: sqlite3.Connection) -> dict:
    """Pour les badges : demandes à confirmer et produits à décider."""
    demandes = conn.execute("SELECT COUNT(*) FROM retours_vendeur WHERE statut=?", (STATUT_ATTENTE,)).fetchone()[0]
    lignes = conn.execute(
        """SELECT COUNT(*) FROM lignes_retour_vendeur l JOIN retours_vendeur r ON r.id = l.retour_id
           WHERE r.statut=? AND l.decision IS NULL""", (STATUT_CONFIRME,),
    ).fetchone()[0]
    return {"demandes": demandes, "lignes": lignes, "total": demandes + lignes}


def situation_depot(conn: sqlite3.Connection) -> dict:
    """Où est la marchandise ? Valeurs au prix d'achat, par compartiment du dépôt."""
    mois = date.today().strftime("%Y-%m")
    stock = conn.execute(
        """SELECT COALESCE(SUM(stock_actuel * COALESCE(prix_achat, 0)), 0) AS vendable,
                  COALESCE(SUM(COALESCE(stock_retours_pieces, 0) * COALESCE(prix_achat, 0)), 0) AS retours,
                  COALESCE(SUM(COALESCE(stock_retours_pieces, 0)), 0) AS retours_pieces
           FROM produits WHERE COALESCE(supprime, 0) = 0""").fetchone()
    camions = conn.execute(
        """SELECT COALESCE(SUM(sc.quantite_pieces * COALESCE(p.prix_achat, 0)), 0)
           FROM stock_camion_vendeur sc JOIN produits p ON p.id = sc.produit_id""").fetchone()[0]
    casse = conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN imputation='VENDEUR' THEN valeur_perte ELSE 0 END), 0),
                  COALESCE(SUM(CASE WHEN imputation='ENTREPRISE' THEN valeur_perte ELSE 0 END), 0)
           FROM lignes_retour_vendeur WHERE decision='CASSE' AND substr(date_decision, 1, 7)=?""", (mois,)).fetchone()
    fourn = conn.execute(
        "SELECT COALESCE(SUM(quantite_pieces * prix_achat), 0) FROM lignes_retour_vendeur WHERE decision='FOURNISSEUR'"
    ).fetchone()[0]
    nb = compter_a_traiter(conn)
    return {
        "stock_vendable_valeur": round(float(stock["vendable"]), 2),
        "retours_a_traiter_valeur": round(float(stock["retours"]), 2),
        "retours_a_traiter_pieces": float(stock["retours_pieces"]),
        "stock_camions_valeur": round(float(camions), 2),
        "casse_mois_vendeur_valeur": round(float(casse[0]), 2),
        "casse_mois_entreprise_valeur": round(float(casse[1]), 2),
        "a_retourner_fournisseur_valeur": round(float(fourn), 2),
        "demandes_en_attente": nb["demandes"],
        "lignes_a_decider": nb["lignes"],
    }
