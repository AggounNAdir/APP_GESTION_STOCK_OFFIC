"""
SERVICE UNIQUE DE TARIFICATION (bureau + comptoir + API + portail).

⚠️ C'est désormais le SEUL endroit où la règle de prix est écrite.
   prix_niveaux.py (PrixSelectorWidget), la vente comptoir et les routers
   de l'API appellent ce module : plus de logique dupliquée, donc plus de
   divergence (dates de validité, source du niveau client, etc.).
   Ce module n'importe pas tkinter : il est utilisable sur le serveur.

Ordre de priorité (le premier trouvé gagne) :
  1. Prix spécial CLIENT × PRODUIT, actif et dans sa période de validité
     (table prix_speciaux_clients).
  2. Palier de quantité pour le niveau du client (table prix_paliers,
     optionnelle : sans ligne dans cette table, rien ne change).
  3. Prix du niveau du client : super_gros / gros / detail / special
     (colonnes produits.prix_*), niveau lu dans clients_niveau_prix puis,
     à défaut, dans clients.niveau_prix. Sans info : « detail ».
  4. Repli sur produits.prix_vente si la colonne du niveau est à 0.

Unités : tous les prix sont par UNITÉ DE BASE (l'unité du stock, la même
que produits.prix_achat). Les quantités passées à `quantite=` doivent donc
être en unités de base aussi (quantité en cartons × facteur_conversion).

Marge : calculée en % du COÛT (même convention que « Calcul par % de marge
sur le Prix d'Achat » dans prix_niveaux.py). Le coût est le prix moyen
pondéré s'il existe, sinon le prix d'achat.

Réglages par variables d'environnement (facultatives) :
  PRIX_MARGE_MIN_PCT      marge minimale en % du coût (défaut 0 = ne pas
                          vendre sous le coût)
  PRIX_CONTROLE_COMMANDES off | warn | enforce (défaut warn : journalise
                          seulement, ne bloque rien)
"""
from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Optional

_log = logging.getLogger("api.princing")

# ═══════════════════════════ CONSTANTES ═══════════════════════════

NIVEAU_DEFAUT = "detail"

NIVEAU_COLONNE = {
    "super_gros": "prix_super_gros",
    "gros": "prix_gros",
    "detail": "prix_detail",
    "special": "prix_special",
}

NIVEAU_LIBELLE = {
    "super_gros": "SUPER GROS",
    "gros": "GROS",
    "detail": "DÉTAIL",
    "special": "SPÉCIAL",
}

SOURCE_SPECIAL_CLIENT = "special_client"
SOURCE_PALIER = "palier"
SOURCE_NIVEAU = "niveau"
SOURCE_PRIX_VENTE = "prix_vente"
SOURCE_INTROUVABLE = "introuvable"

STATUT_OK = "ok"
STATUT_SOUS_MARGE = "sous_marge"
STATUT_SOUS_COUT = "sous_cout"
STATUT_COUT_INCONNU = "cout_inconnu"


# ═══════════════════════════ RÉSULTATS ═══════════════════════════

@dataclass(frozen=True)
class PrixResult:
    """Prix retenu + explication (pour l'afficher à l'écran ou le journaliser)."""
    prix: float
    source: str
    niveau: str
    qte_min: Optional[float] = None  # renseigné si source == palier

    @property
    def libelle(self) -> str:
        if self.source == SOURCE_SPECIAL_CLIENT:
            return "Prix spécial client ★"
        if self.source == SOURCE_PALIER:
            q = f"{self.qte_min:g}" if self.qte_min is not None else "?"
            return f"Palier ≥ {q} ({NIVEAU_LIBELLE.get(self.niveau, self.niveau)})"
        if self.source == SOURCE_NIVEAU:
            return f"Niveau {NIVEAU_LIBELLE.get(self.niveau, self.niveau)}"
        if self.source == SOURCE_PRIX_VENTE:
            return "Prix standard (niveau non renseigné)"
        return "Produit introuvable"


@dataclass(frozen=True)
class MargeResult:
    statut: str
    prix: float
    cout: float
    marge_pct: Optional[float]  # None si coût inconnu
    marge_min_pct: float

    @property
    def ok(self) -> bool:
        return self.statut in (STATUT_OK, STATUT_COUT_INCONNU)

    @property
    def message(self) -> str:
        if self.statut == STATUT_SOUS_COUT:
            return (f"Prix {self.prix:,.2f} DA inférieur au coût "
                    f"({self.cout:,.2f} DA) : vente à perte.")
        if self.statut == STATUT_SOUS_MARGE:
            return (f"Marge {self.marge_pct:.1f} % inférieure au minimum "
                    f"autorisé ({self.marge_min_pct:.1f} %).")
        return ""


@dataclass(frozen=True)
class AnomaliePrix:
    produit_id: int
    message: str
    bloquant: bool


# ═══════════════════════════ OUTILS INTERNES ═══════════════════════════

def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _get(item: Any, name: str, default: Any = None) -> Any:
    """Lit un champ sur un dict OU un objet (modèle pydantic)."""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _normaliser_niveau(niveau: Any) -> str:
    n = str(niveau or "").strip().lower()
    return n if n in NIVEAU_COLONNE else NIVEAU_DEFAUT


def marge_min_defaut() -> float:
    try:
        return float(os.environ.get("PRIX_MARGE_MIN_PCT", "0"))
    except ValueError:
        return 0.0


def mode_controle_commandes() -> str:
    m = os.environ.get("PRIX_CONTROLE_COMMANDES", "warn").strip().lower()
    return m if m in ("off", "warn", "enforce") else "warn"


# ═══════════════════════════ NIVEAU DU CLIENT ═══════════════════════════

def get_niveau_client(conn: sqlite3.Connection, client_id: Optional[int]) -> str:
    """Niveau de prix du client (« detail » si inconnu ou client absent)."""
    if not client_id:
        return NIVEAU_DEFAUT
    niveau = None
    try:
        row = conn.execute(
            "SELECT niveau FROM clients_niveau_prix WHERE client_id=?", (client_id,)
        ).fetchone()
        if row and row[0]:
            niveau = row[0]
    except sqlite3.OperationalError:
        pass  # table absente : base pas encore migrée
    if not niveau:
        try:
            row = conn.execute(
                "SELECT niveau_prix FROM clients WHERE id=?", (client_id,)
            ).fetchone()
            if row and row[0]:
                niveau = row[0]
        except sqlite3.OperationalError:
            pass  # colonne absente
    return _normaliser_niveau(niveau)


# ═══════════════════════════ RÉSOLUTION DU PRIX ═══════════════════════════

def _prix_special_client(conn, client_id, produit_id, jour: str) -> Optional[float]:
    try:
        row = conn.execute(
            """SELECT prix_special FROM prix_speciaux_clients
               WHERE client_id=? AND produit_id=? AND actif=1
                 AND (date_debut IS NULL OR date_debut = '' OR date_debut <= ?)
                 AND (date_fin   IS NULL OR date_fin   = '' OR date_fin   >= ?)""",
            (client_id, produit_id, jour, jour),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if row and _f(row[0]) > 0:
        return _f(row[0])
    return None


def _prix_palier(conn, produit_id, niveau: str, quantite: float):
    """(prix, qte_min) du meilleur palier atteint, ou None."""
    try:
        row = conn.execute(
            """SELECT prix, qte_min FROM prix_paliers
               WHERE produit_id=? AND niveau=? AND actif=1
                 AND prix > 0 AND qte_min <= ?
               ORDER BY qte_min DESC LIMIT 1""",
            (produit_id, niveau, quantite),
        ).fetchone()
    except sqlite3.OperationalError:
        return None  # table prix_paliers absente : fonctionnalité inactive
    return (_f(row[0]), _f(row[1])) if row else None


def resoudre_prix(
    conn: sqlite3.Connection,
    produit_id: int,
    client_id: Optional[int] = None,
    quantite: Optional[float] = None,
    niveau: Optional[str] = None,
    jour: Optional[str] = None,
) -> PrixResult:
    """
    Prix unitaire applicable (par unité de base).

    client_id : client concerné (None = comptoir anonyme → niveau « detail »).
    quantite  : quantité en unités de base, pour les paliers (None = ignorés).
    niveau    : force un niveau (choix MANUEL du vendeur). Dans ce cas le prix
                spécial client est ignoré et le niveau du client n'est pas lu.
    jour      : date ISO de référence (défaut : aujourd'hui).
    """
    jour = jour or date.today().isoformat()
    force = niveau is not None
    niveau_eff = _normaliser_niveau(niveau) if force else get_niveau_client(conn, client_id)

    # 1. Prix spécial client (jamais si le niveau est forcé à la main)
    if client_id and not force:
        sp = _prix_special_client(conn, client_id, produit_id, jour)
        if sp is not None:
            return PrixResult(sp, SOURCE_SPECIAL_CLIENT, "special")

    # 2. Palier de quantité pour ce niveau
    if quantite and quantite > 0:
        pal = _prix_palier(conn, produit_id, niveau_eff, float(quantite))
        if pal is not None:
            return PrixResult(pal[0], SOURCE_PALIER, niveau_eff, qte_min=pal[1])

    # 3. Prix du niveau, 4. repli prix_vente
    col = NIVEAU_COLONNE[niveau_eff]
    row = conn.execute(
        f"SELECT {col}, prix_vente FROM produits WHERE id=?", (produit_id,)
    ).fetchone()
    if row is None:
        return PrixResult(0.0, SOURCE_INTROUVABLE, niveau_eff)
    val = _f(row[0])
    if val > 0:
        return PrixResult(val, SOURCE_NIVEAU, niveau_eff)
    return PrixResult(_f(row[1]), SOURCE_PRIX_VENTE, niveau_eff)


def resolve_prix(conn, client_id, produit_id, quantite=None) -> float:
    """Compatibilité : ancienne signature utilisée par les routers de l'API."""
    return resoudre_prix(conn, produit_id, client_id=client_id, quantite=quantite).prix


# ═══════════════════════════ PALIERS : LECTURE / ÉCRITURE / VALIDATION ═══════════════════════════

def normaliser_paliers(paliers: Iterable[Any]) -> list[dict]:
    """
    Nettoie une liste de paliers ({niveau, qte_min, prix}) : niveau connu,
    quantité et prix > 0, doublons (niveau, qte_min) fusionnés (le dernier
    gagne), résultat trié par niveau puis par quantité.
    """
    ordre = {n: i for i, n in enumerate(NIVEAU_COLONNE)}
    uniques: dict = {}
    for p in paliers:
        niveau = str(_get(p, "niveau", "") or "").strip().lower()
        qte, prix = _f(_get(p, "qte_min")), _f(_get(p, "prix"))
        if niveau not in NIVEAU_COLONNE or qte <= 0 or prix <= 0:
            continue
        uniques[(niveau, qte)] = {"niveau": niveau, "qte_min": qte, "prix": prix}
    return sorted(uniques.values(), key=lambda p: (ordre[p["niveau"]], p["qte_min"]))


def lire_paliers(conn: sqlite3.Connection, produit_id: int) -> list[dict]:
    """Paliers actifs d'un produit (liste vide si la table n'existe pas encore)."""
    try:
        rows = conn.execute(
            "SELECT niveau, qte_min, prix FROM prix_paliers WHERE produit_id=? AND actif=1",
            (produit_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return normaliser_paliers(
        {"niveau": r[0], "qte_min": r[1], "prix": r[2]} for r in rows
    )


def enregistrer_paliers(conn: sqlite3.Connection, produit_id: int, paliers: Iterable[Any]) -> int:
    """
    Remplace les paliers ACTIFS du produit par la liste donnée (ajoute, met à
    jour, supprime). Ne fait pas de commit : à appeler dans la transaction de
    l'enregistrement du produit. Les paliers désactivés à la main (actif=0)
    ne sont pas touchés. Retourne le nombre de paliers enregistrés.
    """
    voulus = normaliser_paliers(paliers)
    cles = {(p["niveau"], p["qte_min"]) for p in voulus}
    for p in voulus:
        conn.execute(
            """INSERT INTO prix_paliers(produit_id, niveau, qte_min, prix, actif)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(produit_id, niveau, qte_min)
               DO UPDATE SET prix = excluded.prix, actif = 1""",
            (produit_id, p["niveau"], p["qte_min"], p["prix"]),
        )
    for r in conn.execute(
        "SELECT id, niveau, qte_min FROM prix_paliers WHERE produit_id=? AND actif=1",
        (produit_id,),
    ).fetchall():
        if (r[1], _f(r[2])) not in cles:
            conn.execute("DELETE FROM prix_paliers WHERE id=?", (r[0],))
    return len(voulus)


def valider_palier(
    niveau: Any,
    qte_min: float,
    prix: float,
    prix_niveau: Optional[float] = None,
    cout: Optional[float] = None,
) -> tuple[Optional[str], list[str]]:
    """
    Contrôle un palier saisi. Retourne (erreur, avertissements) :
      • erreur (str) → à refuser ; None si la saisie est acceptable
        (y compris un prix inférieur au prix d'achat, si `cout` est connu) ;
      • avertissements → à confirmer par l'utilisateur (palier plus cher que
        le prix normal du niveau).
    """
    if str(niveau or "").strip().lower() not in NIVEAU_COLONNE:
        return "Niveau de prix inconnu.", []
    if _f(qte_min) <= 0:
        return "La quantité minimale doit être supérieure à 0.", []
    if _f(prix) <= 0:
        return "Le prix du palier doit être supérieur à 0.", []
    if cout and _f(cout) > 0 and round(_f(prix), 2) < round(_f(cout), 2):
        return (
            f"Le prix du palier ({_f(prix):,.2f} DA) est inférieur au prix d'achat "
            f"({_f(cout):,.2f} DA) : refusé."
        ), []
    avert: list[str] = []
    if prix_niveau and _f(prix_niveau) > 0 and _f(prix) > _f(prix_niveau):
        avert.append(
            f"Le prix du palier ({_f(prix):,.2f} DA) est SUPÉRIEUR au prix normal "
            f"du niveau ({_f(prix_niveau):,.2f} DA). Un palier sert d'habitude à baisser le prix."
        )
    return None, avert


def verifier_coherence_paliers(paliers: Iterable[Any]) -> list[str]:
    """
    Avertissements de cohérence : pour un même niveau, un palier à quantité
    plus élevée ne doit pas être PLUS CHER qu'un palier à quantité plus faible.
    """
    avert: list[str] = []
    precedent: dict = {}
    for p in normaliser_paliers(paliers):
        prev = precedent.get(p["niveau"])
        if prev and p["prix"] > prev["prix"]:
            avert.append(
                f"{NIVEAU_LIBELLE[p['niveau']]} : le palier à partir de {p['qte_min']:g} "
                f"({p['prix']:,.2f} DA) est plus cher que celui à partir de "
                f"{prev['qte_min']:g} ({prev['prix']:,.2f} DA)."
            )
        precedent[p["niveau"]] = p
    return avert


# ═══════════════════════════ AUCUN PRIX DE VENTE SOUS LE PRIX D'ACHAT (fiche produit) ═══════════════════════════

def prix_sous_le_cout(
    prix_achat: Any,
    prix_par_niveau: dict,
    paliers: Iterable[Any] = (),
) -> list[str]:
    """
    Messages d'erreur pour chaque prix de vente SAISI qui est inférieur au prix
    d'achat : les 4 niveaux (super_gros, gros, detail, special) et les paliers.
    Liste vide = tout est accepté. Une règle stricte : un prix égal au prix
    d'achat est accepté. Sont ignorés : un niveau vide / à 0 (non saisi), et
    tout le contrôle si le prix d'achat est inconnu (0).
    """
    cout = _f(prix_achat)
    if cout <= 0:
        return []
    cout2 = round(cout, 2)
    erreurs: list[str] = []
    for niveau in NIVEAU_COLONNE:                       # ordre stable d'affichage
        prix = _f(prix_par_niveau.get(niveau))
        if prix > 0 and round(prix, 2) < cout2:
            erreurs.append(
                f"Prix {NIVEAU_LIBELLE[niveau].title()} : {prix:,.2f} DA "
                f"< prix d'achat {cout:,.2f} DA"
            )
    for p in normaliser_paliers(paliers):
        if round(p["prix"], 2) < cout2:
            erreurs.append(
                f"Palier {NIVEAU_LIBELLE[p['niveau']].title()} à partir de {p['qte_min']:g} : "
                f"{p['prix']:,.2f} DA < prix d'achat {cout:,.2f} DA"
            )
    return erreurs


# ═══════════════════════════ PRIX DE VENTE PAR DÉFAUT (fiche produit) ═══════════════════════════

# Quand le prix Détail n'est pas saisi, produits.prix_vente = prix d'achat × ce coefficient.
COEF_PRIX_VENTE_DEFAUT = 1.35


def prix_vente_defaut(prix_achat: Any, prix_detail: Any) -> float:
    """
    Valeur enregistrée dans produits.prix_vente : le prix Détail s'il est saisi,
    sinon le prix d'achat + 35 %. C'est aussi le prix appliqué à la vente pour
    tout niveau (Super Gros, Gros, Spécial) laissé vide (voir resoudre_prix).
    """
    detail = _f(prix_detail)
    return detail if detail > 0 else _f(prix_achat) * COEF_PRIX_VENTE_DEFAUT


def avertissement_prix_detail(prix_achat: Any, prix_detail: Any) -> Optional[str]:
    """
    Message à montrer avant d'enregistrer une fiche produit dont le prix Détail
    est vide (None si le prix Détail est saisi). À confirmer par l'utilisateur.
    """
    if _f(prix_detail) > 0:
        return None
    pv = prix_vente_defaut(prix_achat, prix_detail)
    if pv > 0:
        return (
            "Le prix Détail est vide.\n\n"
            f"À la vente, le produit sera au prix d'achat + 35 % = {pv:,.2f} DA, "
            "et tous les niveaux laissés vides (Super Gros, Gros, Spécial) "
            "seront aussi à ce prix."
        )
    return (
        "Le prix Détail et le prix d'achat sont vides.\n\n"
        "Le produit sera à 0 DA et impossible à vendre tant qu'un prix n'est pas saisi."
    )


# ═══════════════════════════ MARGE ═══════════════════════════

def cout_produit(conn: sqlite3.Connection, produit_id: int) -> float:
    row = conn.execute(
        "SELECT prix_moyen_pondere, prix_achat FROM produits WHERE id=?", (produit_id,)
    ).fetchone()
    if row is None:
        return 0.0
    pmp, pa = _f(row[0]), _f(row[1])
    return pmp if pmp > 0 else pa


def verifier_marge(
    conn: sqlite3.Connection,
    produit_id: int,
    prix: float,
    marge_min_pct: Optional[float] = None,
) -> MargeResult:
    """Contrôle un prix de vente contre le coût du produit."""
    mini = marge_min_defaut() if marge_min_pct is None else float(marge_min_pct)
    prix = _f(prix)
    cout = cout_produit(conn, produit_id)
    if cout <= 0:
        return MargeResult(STATUT_COUT_INCONNU, prix, 0.0, None, mini)
    marge = (prix - cout) / cout * 100.0
    if prix < cout:
        return MargeResult(STATUT_SOUS_COUT, prix, cout, marge, mini)
    if marge < mini:
        return MargeResult(STATUT_SOUS_MARGE, prix, cout, marge, mini)
    return MargeResult(STATUT_OK, prix, cout, marge, mini)


# ═══════════════════════════ CONTRÔLE DES COMMANDES (API) ═══════════════════════════

def controler_lignes_commande(
    conn: sqlite3.Connection,
    client_id: Optional[int],
    lignes: Iterable[Any],
    est_vendeur: bool,
    mode: Optional[str] = None,
    tolerance: float = 0.01,
) -> list[AnomaliePrix]:
    """
    Compare les prix reçus (portail / mobile) au tarif du serveur.

    Règles :
      • Client du portail (pas vendeur) : un prix inférieur au tarif calculé
        est une anomalie (le client ne négocie pas).
      • Vendeur : libre de négocier, mais un prix sous le coût / sous la marge
        minimale est une anomalie.
      • Prospect (client_id None) : seul le contrôle de marge s'applique.

    Modes : off → rien ; warn → journalise, aucune anomalie bloquante (défaut) ;
    enforce → les anomalies sont marquées `bloquant=True` (le router refuse).
    Une ligne sans prix (0) est ignorée : le router applique alors le tarif.
    """
    mode = mode or mode_controle_commandes()
    if mode == "off":
        return []

    anomalies: list[AnomaliePrix] = []
    for item in lignes:
        pid = int(_get(item, "produit_id", 0) or 0)
        prix_recu = _f(_get(item, "prix_unitaire", 0))
        if not pid or prix_recu <= 0:
            continue
        facteur = _f(_get(item, "facteur_conversion", 1)) or 1.0
        qte_base = _f(_get(item, "quantite", 0)) * facteur

        if client_id and not est_vendeur:
            attendu = resoudre_prix(conn, pid, client_id=client_id, quantite=qte_base).prix
            if attendu > 0 and prix_recu < attendu - tolerance:
                anomalies.append(AnomaliePrix(
                    pid,
                    f"Produit {pid} : prix reçu {prix_recu:,.2f} < tarif {attendu:,.2f}",
                    True,
                ))

        m = verifier_marge(conn, pid, prix_recu)
        if not m.ok:
            anomalies.append(AnomaliePrix(pid, f"Produit {pid} : {m.message}", True))

    if mode == "warn":
        for a in anomalies:
            _log.warning("[contrôle prix] client=%s vendeur=%s %s",
                         client_id, est_vendeur, a.message)
        return [AnomaliePrix(a.produit_id, a.message, False) for a in anomalies]
    return anomalies
