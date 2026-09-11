"""
Résolution du prix de vente pour un client donné.

⚠️ Cette logique reproduit volontairement celle de prix_niveaux.py
(get_prix_produit / get_niveau_client) de l'application bureau, sans en
importer le module (qui dépend de tkinter, inutile/indésirable sur un
serveur d'API). Si vous modifiez les règles de prix dans prix_niveaux.py,
répercutez le changement ici.

Ordre de priorité (le premier trouvé gagne) :
  1. Prix spécial actif et dans sa période de validité pour CE client
     (table prix_speciaux_clients).
  2. Prix du niveau assigné au client (super_gros / gros / detail / special),
     avec repli sur prix_vente si la colonne du niveau est à 0.
"""
import sqlite3
from datetime import date

_NIVEAU_COL = {
    "super_gros": "prix_super_gros",
    "gros": "prix_gros",
    "detail": "prix_detail",
    "special": "prix_special",
}


def get_niveau_client(conn: sqlite3.Connection, client_id: int) -> str:
    row = conn.execute(
        "SELECT niveau FROM clients_niveau_prix WHERE client_id=?", (client_id,)
    ).fetchone()
    return row["niveau"] if row else "detail"


def resolve_prix(conn: sqlite3.Connection, client_id: int, produit_id: int) -> float:
    """Retourne le prix unitaire applicable à ce client pour ce produit."""
    today = date.today().isoformat()
    special = conn.execute(
        """SELECT prix_special FROM prix_speciaux_clients
           WHERE client_id=? AND produit_id=? AND actif=1
             AND (date_debut IS NULL OR date_debut <= ?)
             AND (date_fin IS NULL OR date_fin >= ?)""",
        (client_id, produit_id, today, today),
    ).fetchone()
    if special is not None and special["prix_special"] not in (None, 0):
        return float(special["prix_special"])

    niveau = get_niveau_client(conn, client_id)
    col = _NIVEAU_COL.get(niveau, "prix_detail")
    row = conn.execute(
        f"SELECT {col} AS prix_niveau, prix_vente FROM produits WHERE id=?",
        (produit_id,),
    ).fetchone()
    if row is None:
        return 0.0
    val = row["prix_niveau"] or 0.0
    return float(val if val > 0 else (row["prix_vente"] or 0.0))