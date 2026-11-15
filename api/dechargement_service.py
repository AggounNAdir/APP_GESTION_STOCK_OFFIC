"""Déchargement contrôlé de fin de tournée (camion vendeur -> dépôt).

Flux :
  1. Le vendeur déclare ce qu'il rend réellement      -> demande « En attente »
     (le camion n'est pas touché ; ventes et chargements sont bloqués).
  2. L'administration valide ou rejette.
       - Validation : le rendu réintègre le dépôt (RETOUR_CAMION), l'écart est
         retiré du camion et tracé, ce qui est « gardé » reste dans le camion.
       - Rejet / annulation : rien ne bouge, le vendeur peut reprendre ses ventes.

Les quantités sont stockées en pièces ; le vendeur les saisit en colis.
Aucune fonction ne fait de commit en dehors de son bloc `with conn`.
"""
import math
import sqlite3
from datetime import date, datetime
from typing import Iterable, Optional

from api.stock_journal import enregistrer_mouvement

STATUT_ATTENTE = "En attente"
STATUT_VALIDE = "Validé"
STATUT_REJETE = "Rejeté"
STATUT_ANNULE = "Annulé"

MOTIF_GARDE = "GARDE"
MOTIFS_ECART = {
    MOTIF_GARDE: "Gardé dans le camion",
    "CASSE": "Casse / produit abîmé",
    "MANQUANT": "Manquant",
    "AUTRE": "Autre",
}
_EPS = 1e-6


def dechargement_en_attente(conn: sqlite3.Connection, vendeur_id: int) -> Optional[sqlite3.Row]:
    """Demande en attente du vendeur, ou None."""
    return conn.execute(
        "SELECT id, numero FROM bons_dechargement WHERE vendeur_id=? AND statut=? ORDER BY id DESC LIMIT 1",
        (vendeur_id, STATUT_ATTENTE),
    ).fetchone()


def compter_en_attente(conn: sqlite3.Connection) -> int:
    """Nombre de demandes de déchargement à traiter, tous vendeurs confondus."""
    return conn.execute(
        "SELECT COUNT(*) FROM bons_dechargement WHERE statut=?", (STATUT_ATTENTE,)
    ).fetchone()[0]


def verifier_aucun_dechargement_en_attente(conn: sqlite3.Connection, vendeur_id: int) -> None:
    attente = dechargement_en_attente(conn, vendeur_id)
    if attente is not None:
        raise ValueError(
            f"Le déchargement {attente['numero']} est en attente de validation : "
            "validez-le, rejetez-le ou annulez-le avant toute autre opération sur ce camion."
        )


def _numero(conn: sqlite3.Connection) -> str:
    jour = date.today().strftime("%Y%m%d")
    n = conn.execute(
        "SELECT COUNT(*) FROM bons_dechargement WHERE numero LIKE ?", (f"DCH-{jour}-%",)
    ).fetchone()[0]
    while True:
        n += 1
        numero = f"DCH-{jour}-{n:04d}"
        if conn.execute("SELECT 1 FROM bons_dechargement WHERE numero=?", (numero,)).fetchone() is None:
            return numero


def _facteur(valeur) -> float:
    try:
        f = float(valeur or 1)
    except (TypeError, ValueError):
        return 1.0
    return f if math.isfinite(f) and f > 0 else 1.0


def creer_demande_dechargement(
    conn: sqlite3.Connection,
    vendeur_id: int,
    lignes: Iterable[tuple],
    observations: str = "",
) -> dict:
    """Crée une demande de déchargement.

    `lignes` : (produit_id, colis_rendus[, motif_ecart]). Tous les produits
    présents dans le camion doivent figurer (0 si rien n'est rendu). Si le rendu
    est inférieur au stock théorique, un motif d'écart est obligatoire.
    """
    saisie: dict[int, tuple[float, Optional[str]]] = {}
    for ligne in lignes:
        produit_id, colis = ligne[0], ligne[1]
        motif = (ligne[2] if len(ligne) > 2 else None) or None
        colis = float(colis)
        if not math.isfinite(colis) or colis < 0:
            raise ValueError("Chaque quantité rendue doit être un nombre positif ou nul.")
        if motif is not None:
            motif = str(motif).strip().upper()
            if motif not in MOTIFS_ECART:
                raise ValueError(f"Motif d'écart inconnu : {motif!r}.")
        if int(produit_id) in saisie:
            raise ValueError("Un produit ne peut apparaître qu'une seule fois dans le déchargement.")
        saisie[int(produit_id)] = (colis, motif)

    with conn:
        vendeur = conn.execute(
            "SELECT id, nom FROM vendeurs WHERE id=? AND actif=1", (vendeur_id,)
        ).fetchone()
        if vendeur is None:
            raise ValueError("Le vendeur sélectionné n'existe pas ou est désactivé.")
        verifier_aucun_dechargement_en_attente(conn, vendeur_id)

        stock = conn.execute(
            """SELECT sc.produit_id, sc.quantite_pieces, p.designation,
                      COALESCE(p.facteur_conversion, 1) AS facteur,
                      COALESCE(p.prix_achat, 0) AS prix_achat
               FROM stock_camion_vendeur sc JOIN produits p ON p.id = sc.produit_id
               WHERE sc.vendeur_id=? AND sc.quantite_pieces > 0""",
            (vendeur_id,),
        ).fetchall()
        if not stock:
            raise ValueError("Le camion est déjà vide : rien à décharger.")

        en_camion = {r["produit_id"]: r for r in stock}
        inconnus = [pid for pid in saisie if pid not in en_camion]
        if inconnus:
            raise ValueError("Produit absent du camion du vendeur : un déchargement ne peut porter que sur le stock embarqué.")
        manquants = [r["designation"] for pid, r in en_camion.items() if pid not in saisie]
        if manquants:
            raise ValueError(
                "Saisissez la quantité rendue (0 si rien) pour : " + ", ".join(manquants) + "."
            )

        details = []
        tot_theo = tot_reel = tot_ecart = valeur = 0.0
        for pid, r in en_camion.items():
            facteur = _facteur(r["facteur"])
            theo = float(r["quantite_pieces"] or 0)
            colis, motif = saisie[pid]
            reel = round(colis * facteur, 6)
            if reel > theo + _EPS:
                raise ValueError(
                    f"{r['designation']} : {colis:g} colis rendus, mais le camion n'en contient "
                    f"que {theo / facteur:g}."
                )
            reel = min(reel, theo)
            ecart = round(theo - reel, 6)
            if ecart > _EPS:
                if motif is None:
                    raise ValueError(
                        f"{r['designation']} : il manque {ecart / facteur:g} colis, indiquez le motif de l'écart."
                    )
            else:
                ecart, motif = 0.0, None
            prix = float(r["prix_achat"] or 0)
            tot_theo += theo
            tot_reel += reel
            if ecart > 0 and motif != MOTIF_GARDE:
                tot_ecart += ecart
                valeur += ecart * prix
            details.append((pid, facteur, theo, reel, ecart, motif, prix))

        numero = _numero(conn)
        maintenant = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            """INSERT INTO bons_dechargement
               (numero, date_demande, vendeur_id, statut, total_theorique_pieces,
                total_reel_pieces, total_ecart_pieces, valeur_ecart, observations)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (numero, maintenant, vendeur_id, STATUT_ATTENTE, tot_theo, tot_reel,
             tot_ecart, round(valeur, 2), (observations or "").strip() or None),
        )
        bon_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO lignes_dechargement
               (dechargement_id, produit_id, facteur, theorique_pieces, reel_pieces,
                ecart_pieces, motif_ecart, prix_unitaire) VALUES (?,?,?,?,?,?,?,?)""",
            [(bon_id, *d) for d in details],
        )
    return detail_dechargement(conn, bon_id)


def valider_dechargement(conn: sqlite3.Connection, bon_id: int, utilisateur: str = "") -> dict:
    """Valide la demande : réintègre le rendu au dépôt et applique l'écart au camion."""
    with conn:
        bon = conn.execute("SELECT * FROM bons_dechargement WHERE id=?", (bon_id,)).fetchone()
        if bon is None:
            raise ValueError("Bon de déchargement introuvable.")
        if bon["statut"] != STATUT_ATTENTE:
            raise ValueError(f"Ce bon est déjà « {bon['statut']} » : il ne peut plus être validé.")
        vendeur = conn.execute("SELECT nom FROM vendeurs WHERE id=?", (bon["vendeur_id"],)).fetchone()
        nom_vendeur = vendeur["nom"] if vendeur else ""

        lignes = conn.execute(
            """SELECT l.*, p.stock_actuel, p.designation
               FROM lignes_dechargement l JOIN produits p ON p.id = l.produit_id
               WHERE l.dechargement_id=?""",
            (bon_id,),
        ).fetchall()

        # Le camion ne doit pas avoir bougé depuis la demande (sinon l'écart n'a plus de sens).
        for l in lignes:
            camion = conn.execute(
                "SELECT quantite_pieces FROM stock_camion_vendeur WHERE vendeur_id=? AND produit_id=?",
                (bon["vendeur_id"], l["produit_id"]),
            ).fetchone()
            actuel = float(camion["quantite_pieces"] or 0) if camion else 0.0
            if abs(actuel - float(l["theorique_pieces"])) > _EPS:
                raise ValueError(
                    f"Le stock camion de {l['designation']} a changé depuis la demande "
                    f"({actuel:g} pièce(s) au lieu de {l['theorique_pieces']:g}). "
                    "Rejetez ce bon et demandez au vendeur d'en refaire un."
                )

        for l in lignes:
            reel = float(l["reel_pieces"])
            garde = float(l["ecart_pieces"]) if l["motif_ecart"] == MOTIF_GARDE else 0.0
            reste_camion = round(garde, 6)
            facteur = _facteur(l["facteur"])
            if reel > 0:
                stock_avant = float(l["stock_actuel"] or 0)
                stock_apres = stock_avant + reel
                conn.execute("UPDATE produits SET stock_actuel=? WHERE id=?", (stock_apres, l["produit_id"]))
                enregistrer_mouvement(
                    conn, l["produit_id"], "RETOUR_CAMION", stock_avant, stock_apres,
                    quantite=reel,
                    document_type="bon_dechargement", document_id=bon_id,
                    document_numero=bon["numero"], tiers_nom=nom_vendeur,
                    motif=f"Déchargement contrôlé {nom_vendeur} ({reel / facteur:g} colis)",
                    utilisateur=utilisateur or None,
                )
            conn.execute(
                """UPDATE stock_camion_vendeur
                   SET quantite_pieces=?, quantite_colis=?, date_maj=datetime('now')
                   WHERE vendeur_id=? AND produit_id=?""",
                (reste_camion, round(reste_camion / facteur, 6), bon["vendeur_id"], l["produit_id"]),
            )

        conn.execute(
            """UPDATE bons_dechargement
               SET statut=?, date_decision=?, decide_par=? WHERE id=?""",
            (STATUT_VALIDE, datetime.now().isoformat(timespec="seconds"), utilisateur or None, bon_id),
        )
    return detail_dechargement(conn, bon_id)


def rejeter_dechargement(conn: sqlite3.Connection, bon_id: int, utilisateur: str, motif: str) -> dict:
    """Rejette la demande : aucun mouvement de stock, le camion reste intact."""
    motif = (motif or "").strip()
    if not motif:
        raise ValueError("Le motif du rejet est obligatoire.")
    with conn:
        bon = conn.execute("SELECT statut FROM bons_dechargement WHERE id=?", (bon_id,)).fetchone()
        if bon is None:
            raise ValueError("Bon de déchargement introuvable.")
        if bon["statut"] != STATUT_ATTENTE:
            raise ValueError(f"Ce bon est déjà « {bon['statut']} » : il ne peut plus être rejeté.")
        conn.execute(
            """UPDATE bons_dechargement
               SET statut=?, date_decision=?, decide_par=?, motif_rejet=? WHERE id=?""",
            (STATUT_REJETE, datetime.now().isoformat(timespec="seconds"), utilisateur or None, motif, bon_id),
        )
    return detail_dechargement(conn, bon_id)


def annuler_demande_dechargement(conn: sqlite3.Connection, bon_id: int, vendeur_id: int) -> dict:
    """Le vendeur retire sa propre demande tant qu'elle n'est pas traitée."""
    with conn:
        bon = conn.execute(
            "SELECT statut FROM bons_dechargement WHERE id=? AND vendeur_id=?", (bon_id, vendeur_id)
        ).fetchone()
        if bon is None:
            raise ValueError("Bon de déchargement introuvable.")
        if bon["statut"] != STATUT_ATTENTE:
            raise ValueError(f"Ce bon est déjà « {bon['statut']} » : il ne peut plus être annulé.")
        conn.execute(
            "UPDATE bons_dechargement SET statut=?, date_decision=? WHERE id=?",
            (STATUT_ANNULE, datetime.now().isoformat(timespec="seconds"), bon_id),
        )
    return detail_dechargement(conn, bon_id)


def detail_dechargement(conn: sqlite3.Connection, bon_id: int) -> dict:
    bon = conn.execute(
        """SELECT b.*, v.nom AS vendeur_nom FROM bons_dechargement b
           LEFT JOIN vendeurs v ON v.id = b.vendeur_id WHERE b.id=?""",
        (bon_id,),
    ).fetchone()
    if bon is None:
        raise ValueError("Bon de déchargement introuvable.")
    lignes = conn.execute(
        """SELECT l.produit_id, p.code, p.designation, l.facteur, l.theorique_pieces,
                  l.reel_pieces, l.ecart_pieces, l.motif_ecart, l.prix_unitaire
           FROM lignes_dechargement l JOIN produits p ON p.id = l.produit_id
           WHERE l.dechargement_id=? ORDER BY p.designation""",
        (bon_id,),
    ).fetchall()
    resultat = dict(bon)
    resultat["lignes"] = []
    for l in lignes:
        d = dict(l)
        f = _facteur(d["facteur"])
        d["theorique_colis"] = round(d["theorique_pieces"] / f, 4)
        d["reel_colis"] = round(d["reel_pieces"] / f, 4)
        d["ecart_colis"] = round(d["ecart_pieces"] / f, 4)
        d["motif_libelle"] = MOTIFS_ECART.get(d["motif_ecart"])
        resultat["lignes"].append(d)
    return resultat


def lister_dechargements(
    conn: sqlite3.Connection,
    vendeur_id: Optional[int] = None,
    statut: Optional[str] = None,
    limite: int = 100,
) -> list:
    sql = """SELECT b.id, b.numero, b.date_demande, b.vendeur_id, v.nom AS vendeur_nom, b.statut,
                    b.total_theorique_pieces, b.total_reel_pieces, b.total_ecart_pieces,
                    b.valeur_ecart, b.observations, b.date_decision, b.decide_par, b.motif_rejet
             FROM bons_dechargement b LEFT JOIN vendeurs v ON v.id = b.vendeur_id WHERE 1=1"""
    params: list = []
    if vendeur_id is not None:
        sql += " AND b.vendeur_id=?"
        params.append(vendeur_id)
    if statut:
        sql += " AND b.statut=?"
        params.append(statut)
    sql += " ORDER BY b.id DESC LIMIT ?"
    params.append(int(limite))
    return [dict(r) for r in conn.execute(sql, params).fetchall()]
