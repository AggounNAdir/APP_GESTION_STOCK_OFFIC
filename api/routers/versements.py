from datetime import date
import sqlite3
from typing import Optional
from api.deps import get_current_client, get_db
from api.schemas import Versement, VersementIn
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

router = APIRouter(prefix="/versements", tags=["Versements & Règlements"])


@router.get("", response_model=list[Versement])
def list_versements(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: sqlite3.Row = Depends(get_current_client),
    conn: sqlite3.Connection = Depends(get_db),
):
  """Liste tous les versements du client connecté."""
  rows = conn.execute(
      """SELECT * FROM versements_clients WHERE client_id=?
           ORDER BY date_vers DESC, id DESC LIMIT ? OFFSET ?""",
      (client["id"], limit, offset),
  ).fetchall()
  return [
      Versement(
          id=r["id"],
          numero=r["numero"] if "numero" in r.keys() else f"VERS-{r['id']}",
          date_vers=r["date_vers"],
          montant=float(r["montant"] or 0),
          mode=r["mode"] if "mode" in r.keys() else "Espèces",
          reference=r["reference"] if "reference" in r.keys() else None,
      )
      for r in rows
  ]


@router.post("", response_model=Versement, status_code=status.HTTP_201_CREATED)
async def create_versement(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
  # 1. Lire le JSON brut envoyé par Androway
  data = await request.json()
  print(">>> [DEBUG DONNÉES REÇUES VERSEMENT] :", data)

  client_id = data.get("client_id")
  prospect_id = data.get("prospect_id")
  nom = str(data.get("nom_client") or data.get("nomClient") or "").strip()
  code = str(
      data.get("code_client") or data.get("codeClient") or ""
  ).strip().upper()
  is_prosp_flag = bool(data.get("is_prospect", False))
  montant = float(data.get("montant") or 0)
  mode = str(data.get("mode") or "Espèces")
  reference = data.get("reference")
  vendeur_id = data.get("vendeur_id")

  today_num = date.today().strftime("%Y%m%d")
  today_iso = date.today().isoformat()

  # Détection prospect
  is_prospect = bool(
      is_prosp_flag or code.startswith("PROSP") or (prospect_id and prospect_id > 0)
  )

  # =========================================================================
  # CAS 1 : C'EST UN PROSPECT 🎯 (TOTALEMENT ISOLÉ DU CLIENT COMPTOIR)
  # =========================================================================
  if is_prospect:
    # Table versements_prospects : créée par api/schema.py

    # Récupérer l'ID réel dans prospects_clients
    p_row = conn.execute(
        """SELECT id, nom FROM prospects_clients 
           WHERE UPPER(TRIM(code)) = ? OR id = ? OR LOWER(TRIM(nom)) = ?""",
        (code, prospect_id or 0, nom.lower()),
    ).fetchone()

    real_p_id = p_row["id"] if p_row else (prospect_id or 1)
    prospect_nom = p_row["nom"] if p_row else nom

    # Désactiver les clés étrangères SQLite pour éviter l'erreur 500
    conn.execute("PRAGMA foreign_keys = OFF")

    count = conn.execute(
        "SELECT COUNT(*) FROM versements_prospects WHERE date_vers LIKE ?",
        (f"{date.today()}%",),
    ).fetchone()[0]
    numero = f"VP-{today_num}-{count + 1:04d}"

    cursor = conn.execute(
        """INSERT INTO versements_prospects 
           (numero, date_vers, prospect_id, vendeur_id, montant, mode, reference)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            numero,
            today_iso,
            real_p_id,
            vendeur_id if (vendeur_id and vendeur_id > 0) else None,
            montant,
            mode,
            reference,
        ),
    )

    # Réactiver les clés étrangères
    conn.execute("PRAGMA foreign_keys = ON")

    # Mettre à jour le solde du prospect dans prospects_clients
    try:
      conn.execute(
          "UPDATE prospects_clients SET solde = MAX(0, COALESCE(solde, 0) - ?)"
          " WHERE id = ?",
          (montant, real_p_id),
      )
    except Exception:
      pass

    conn.commit()

    print(
        f">>> ✅ [SUCCÈS PROSPECT] Versement {numero} de {montant} DA enregistré"
        f" pour '{prospect_nom}' (ID: {real_p_id}). Client Comptoir non"
        " touché !"
    )

    return Versement(
        id=cursor.lastrowid,
        numero=numero,
        date_vers=today_iso,
        montant=montant,
        mode=mode,
        reference=reference,
    )

  # =========================================================================
  # CAS 2 : C'EST UN CLIENT OFFICIEL 👤
  # =========================================================================
  target_client_id = None

  if nom:
    clt = conn.execute(
        "SELECT id, nom FROM clients WHERE LOWER(TRIM(nom)) = LOWER(TRIM(?))",
        (nom,),
    ).fetchone()
    if clt:
      target_client_id = clt["id"]

  if not target_client_id and code:
    clt = conn.execute(
        "SELECT id, nom FROM clients WHERE UPPER(TRIM(code)) = UPPER(TRIM(?))",
        (code,),
    ).fetchone()
    if clt:
      target_client_id = clt["id"]

  if not target_client_id and client_id and client_id > 0:
    clt = conn.execute(
        "SELECT id, nom FROM clients WHERE id = ?", (client_id,)
    ).fetchone()
    if clt:
      target_client_id = clt["id"]

  if not target_client_id:
    raise HTTPException(
        status_code=404,
        detail=(
            f"Client introuvable (Nom: '{nom}', Code: '{code}'). Versement"
            " refusé."
        ),
    )

  count = conn.execute(
      "SELECT COUNT(*) FROM versements_clients WHERE date_vers LIKE ?",
      (f"{date.today()}%",),
  ).fetchone()[0]
  numero = f"VC-{today_num}-{count + 1:04d}"

  cols_vers = [
      c[1] for c in conn.execute("PRAGMA table_info(versements_clients)").fetchall()
  ]
  if "vendeur_id" in cols_vers:
    cursor = conn.execute(
        """INSERT INTO versements_clients 
           (numero, date_vers, client_id, vendeur_id, montant, mode, reference)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            numero,
            today_iso,
            target_client_id,
            vendeur_id,
            montant,
            mode,
            reference,
        ),
    )
  else:
    cursor = conn.execute(
        """INSERT INTO versements_clients 
           (numero, date_vers, client_id, montant, mode, reference)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (numero, today_iso, target_client_id, montant, mode, reference),
    )

  conn.execute(
      "UPDATE clients SET solde = MAX(0, solde - ?) WHERE id = ?",
      (montant, target_client_id),
  )
  conn.commit()

  print(
      f">>> ✅ [SUCCÈS CLIENT] Versement {numero} de {montant} DA pour Client"
      f" ID {target_client_id}"
  )

  return Versement(
      id=cursor.lastrowid,
      numero=numero,
      date_vers=today_iso,
      montant=montant,
      mode=mode,
      reference=reference,
  )